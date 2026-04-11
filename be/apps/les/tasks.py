import logging

from celery import Task

from memo_backend.celery import app
from apps.les.models import LessonIngestionJob, LessonIngestionJobStatus
from apps.les.models.lesson_ingestion_job_model import (
    LessonIngestionJobType,
    LessonIngestionTriggerSource,
)
from apps.les.services.lesson_ingestion_scheduling_service import schedule_lesson_ingestion
from apps.app_server.models.lesson_model import (
    Lesson,
    TRANSCRIPT_STATUS_FAILED,
    TRANSCRIPT_STATUS_PROCESSING,
    TRANSCRIPT_STATUS_READY,
)
from apps.les.services.lesson_ingestion_processing_service import (
    LessonIngestionProcessingError,
    mark_job_completed,
    mark_job_failed,
    mark_job_processing,
    orchestrate_lesson_ingestion_job,
)
from apps.les.services.lesson_video_transcription_service import transcribe_lesson_video
from apps.app_server.services.lesson_publication_service import reconcile_lesson_publication

logger = logging.getLogger(__name__)


class LessonIngestionTaskBase(Task):
    """Shared task behaviors for lesson ingestion jobs."""


@app.task(base=LessonIngestionTaskBase, name='lesson_ingestion.process_lesson_ingestion_job')
def process_lesson_ingestion_job(job_id):
    try:
        job = LessonIngestionJob.objects.get(id=job_id)
    except LessonIngestionJob.DoesNotExist:
        return

    # Basic idempotency: only process pending jobs.
    if job.status != LessonIngestionJobStatus.PENDING:
        return

    mark_job_processing(job)
    try:
        orchestrate_lesson_ingestion_job(job)
    except Exception as exc:
        error_payload = getattr(exc, 'error_payload', None)
        if not error_payload and isinstance(exc, LessonIngestionProcessingError):
            error_payload = exc.error_payload
        if not error_payload:
            error_payload = {'error_type': exc.__class__.__name__}
        mark_job_failed(job, error_message=str(exc), error_payload=error_payload)
        reconcile_lesson_publication(job.lesson)
        return

    mark_job_completed(job)
    reconcile_lesson_publication(job.lesson)


@app.task(name='lesson_ingestion.process_lesson_video_transcription')
def process_lesson_video_transcription(lesson_id):
    lesson = Lesson.all_objects.filter(id=lesson_id, is_deleted=False).first()
    if lesson is None or not lesson.video_file:
        return

    lesson.transcript_status = TRANSCRIPT_STATUS_PROCESSING
    lesson.transcript_error = ''
    lesson.save(update_fields=['transcript_status', 'transcript_error', 'updated_at'])

    try:
        transcript_text = transcribe_lesson_video(
            video_path=lesson.video_file.path,
            language=lesson.transcript_language or 'en',
        )
    except Exception:
        logger.exception('Lesson transcript task failed for lesson_id=%s', lesson_id)
        lesson.transcript_status = TRANSCRIPT_STATUS_FAILED
        lesson.transcript_error = 'Lesson video transcription failed.'
        lesson.save(update_fields=['transcript_status', 'transcript_error', 'updated_at'])
        reconcile_lesson_publication(lesson)
        return

    lesson.transcript_text = transcript_text
    lesson.transcript_status = TRANSCRIPT_STATUS_READY
    lesson.transcript_error = ''
    lesson.save(update_fields=['transcript_text', 'transcript_status', 'transcript_error', 'updated_at'])
    has_existing_ingestion = LessonIngestionJob.objects.filter(lesson=lesson).exclude(
        job_type=LessonIngestionJobType.DELETE_INDEX,
    ).exists()
    schedule_lesson_ingestion(
        lesson,
        trigger_source=(
            LessonIngestionTriggerSource.LESSON_UPDATED
            if has_existing_ingestion
            else LessonIngestionTriggerSource.LESSON_CREATED
        ),
        job_type=(
            LessonIngestionJobType.REINGEST
            if has_existing_ingestion
            else LessonIngestionJobType.INGEST
        ),
    )
    reconcile_lesson_publication(lesson)
