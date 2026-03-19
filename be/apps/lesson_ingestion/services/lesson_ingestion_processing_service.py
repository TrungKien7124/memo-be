from django.utils import timezone

from apps.lesson_ingestion.models import LessonIngestionJob, LessonIngestionJobStatus


def orchestrate_lesson_ingestion_job(job: LessonIngestionJob) -> None:
    """
    Placeholder orchestration for Sprint 2.
    Extraction/chunking/indexing is intentionally out of scope for now.
    """
    # In a later step, this function will:
    # 1) resolve extraction source (text_markdown / video_url_transcript)
    # 2) persist normalized sources
    # 3) chunk content + persist chunks with vector_document_id metadata
    # 4) update vector store and mark job completed
    _ = job


def mark_job_processing(job: LessonIngestionJob) -> None:
    job.status = LessonIngestionJobStatus.PROCESSING
    job.started_at = timezone.now()
    job.save(update_fields=['status', 'started_at', 'updated_at'])


def mark_job_completed(job: LessonIngestionJob) -> None:
    job.status = LessonIngestionJobStatus.COMPLETED
    job.finished_at = timezone.now()
    job.save(update_fields=['status', 'finished_at', 'updated_at'])


def mark_job_failed(job: LessonIngestionJob, error_message: str, error_payload=None) -> None:
    job.status = LessonIngestionJobStatus.FAILED
    job.finished_at = timezone.now()
    job.error_message = error_message[:2000]
    job.error_payload = error_payload or {}
    job.save(update_fields=['status', 'finished_at', 'error_message', 'error_payload', 'updated_at'])

