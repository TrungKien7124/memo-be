from __future__ import annotations

from apps.app_server.models.implemented.cms_lesson_model import Lesson
from apps.lesson_ingestion.models import LessonContentChunk, LessonIngestionJob, LessonIngestionJobStatus
from apps.lesson_ingestion.services.lesson_ingestion_scheduling_service import is_ingestion_supported_lesson


def _latest_job_summary(job: LessonIngestionJob | None) -> dict | None:
    if job is None:
        return None

    return {
        'id': job.id,
        'job_type': job.job_type,
        'trigger_source': job.trigger_source,
        'status': job.status,
        'source_version': job.source_version,
        'started_at': job.started_at,
        'finished_at': job.finished_at,
        'created_at': job.created_at,
    }


def _latest_failed_job_summary(job: LessonIngestionJob | None) -> dict | None:
    if job is None:
        return None

    failed_summary = _latest_job_summary(job) or {}
    failed_summary.update(
        {
            'error_message': job.error_message,
            'error_payload': job.error_payload,
        },
    )
    return failed_summary


def get_lesson_ingestion_status(lesson: Lesson) -> dict:
    supported_for_ingestion = is_ingestion_supported_lesson(lesson)

    active_chunks_qs = LessonContentChunk.objects.filter(lesson=lesson, is_active=True)
    active_chunk_count = active_chunks_qs.count()
    has_active_chunk_set = active_chunk_count > 0

    latest_job = LessonIngestionJob.objects.filter(lesson=lesson).order_by('-created_at').first()
    latest_completed_job = (
        LessonIngestionJob.objects.filter(lesson=lesson, status=LessonIngestionJobStatus.COMPLETED)
        .order_by('-finished_at', '-created_at')
        .first()
    )
    latest_failed_job = (
        LessonIngestionJob.objects.filter(lesson=lesson, status=LessonIngestionJobStatus.FAILED)
        .order_by('-finished_at', '-created_at')
        .first()
    )

    latest_active_completed_job = (
        LessonIngestionJob.objects.filter(lesson=lesson, status=LessonIngestionJobStatus.COMPLETED, content_chunks__is_active=True)
        .order_by('-finished_at', '-created_at')
        .first()
    )

    last_indexed_at = (
        latest_active_completed_job.finished_at
        if latest_active_completed_job is not None
        else None
    )

    return {
        'lesson_id': lesson.id,
        'supported_for_ingestion': supported_for_ingestion,
        'lesson_type': lesson.lesson_type,
        'latest_job': _latest_job_summary(latest_job),
        'latest_completed_job_id': latest_completed_job.id if latest_completed_job is not None else None,
        'latest_failed_job': _latest_failed_job_summary(latest_failed_job),
        'active_chunk_count': active_chunk_count,
        'has_active_chunk_set': has_active_chunk_set,
        'last_indexed_at': last_indexed_at,
    }

