from celery import Task

from memo_backend.celery import app
from apps.lesson_ingestion.models import LessonIngestionJob, LessonIngestionJobStatus
from apps.lesson_ingestion.services.lesson_ingestion_processing_service import (
    LessonIngestionProcessingError,
    mark_job_completed,
    mark_job_failed,
    mark_job_processing,
    orchestrate_lesson_ingestion_job,
)


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
        return

    mark_job_completed(job)

