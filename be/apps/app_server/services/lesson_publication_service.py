"""
Derive and persist learner publication fields from transcript and ingestion state.
"""

from __future__ import annotations

from django.conf import settings

from apps.app_server.models.lesson_model import (
    LESSON_TYPE_QUIZ,
    TRANSCRIPT_STATUS_FAILED,
    TRANSCRIPT_STATUS_NOT_STARTED,
    TRANSCRIPT_STATUS_PROCESSING,
    TRANSCRIPT_STATUS_READY,
    Lesson,
    PUBLICATION_STATUS_DRAFT,
    PUBLICATION_STATUS_FAILED,
    PUBLICATION_STATUS_PROCESSING,
    PUBLICATION_STATUS_READY,
)
from apps.les.models import LessonIngestionJobStatus
from apps.les.services.lesson_ingestion_scheduling_service import is_ingestion_supported_lesson
from apps.les.services.lesson_ingestion_status_service import get_lesson_ingestion_status


def _persist_publication(lesson: Lesson, publication_status: str, is_active: bool, publication_error: str) -> None:
    publication_error = (publication_error or '')[:2000]
    if (
        lesson.publication_status == publication_status
        and lesson.is_active == is_active
        and lesson.publication_error == publication_error
    ):
        return
    lesson.publication_status = publication_status
    lesson.is_active = is_active
    lesson.publication_error = publication_error
    lesson.save(update_fields=['publication_status', 'is_active', 'publication_error', 'updated_at'])


def reconcile_lesson_publication(lesson: Lesson) -> None:
    """
    Recompute publication_status, is_active, and publication_error from pipeline state.

    Quiz lessons publish immediately. Lesson-type rows wait on transcript (when a video
    file is present) and on ingestion rules that depend on AI_RAG_ENABLED.
    """
    if lesson.is_deleted:
        return

    lesson.refresh_from_db()
    if lesson.lesson_type == LESSON_TYPE_QUIZ:
        _persist_publication(lesson, PUBLICATION_STATUS_READY, True, '')
        return

    if not is_ingestion_supported_lesson(lesson):
        _persist_publication(lesson, PUBLICATION_STATUS_READY, True, '')
        return

    ingestion = get_lesson_ingestion_status(lesson)
    rag_enabled = getattr(settings, 'AI_RAG_ENABLED', False)
    latest_job = ingestion.get('latest_job')
    job_status = (latest_job or {}).get('status')

    if (
        job_status == LessonIngestionJobStatus.FAILED
        and not ingestion.get('has_active_chunk_set')
    ):
        failed = ingestion.get('latest_failed_job') or {}
        _persist_publication(
            lesson,
            PUBLICATION_STATUS_FAILED,
            False,
            failed.get('error_message') or 'Ingestion failed.',
        )
        return

    has_video_file = bool((getattr(lesson.video_file, 'name', None) or '').strip())
    if has_video_file:
        transcript_state = lesson.transcript_status
        if transcript_state == TRANSCRIPT_STATUS_FAILED:
            _persist_publication(
                lesson,
                PUBLICATION_STATUS_FAILED,
                False,
                lesson.transcript_error or 'Transcript failed.',
            )
            return
        if transcript_state in (TRANSCRIPT_STATUS_NOT_STARTED, TRANSCRIPT_STATUS_PROCESSING):
            _persist_publication(lesson, PUBLICATION_STATUS_PROCESSING, False, '')
            return
        if transcript_state != TRANSCRIPT_STATUS_READY:
            _persist_publication(lesson, PUBLICATION_STATUS_PROCESSING, False, '')
            return

    if latest_job is None and not ingestion.get('latest_failed_job') and not ingestion.get('has_active_chunk_set'):
        _persist_publication(lesson, PUBLICATION_STATUS_DRAFT, False, '')
        return

    if job_status in (LessonIngestionJobStatus.PENDING, LessonIngestionJobStatus.PROCESSING):
        _persist_publication(lesson, PUBLICATION_STATUS_PROCESSING, False, '')
        return

    if not rag_enabled:
        if job_status == LessonIngestionJobStatus.FAILED and not ingestion.get('has_active_chunk_set'):
            failed = ingestion.get('latest_failed_job') or {}
            _persist_publication(
                lesson,
                PUBLICATION_STATUS_FAILED,
                False,
                failed.get('error_message') or 'Ingestion failed.',
            )
            return
        if ingestion.get('has_active_chunk_set'):
            _persist_publication(lesson, PUBLICATION_STATUS_READY, True, '')
            return
        if job_status == LessonIngestionJobStatus.COMPLETED:
            _persist_publication(lesson, PUBLICATION_STATUS_READY, True, '')
            return
        _persist_publication(lesson, PUBLICATION_STATUS_PROCESSING, False, '')
        return

    if ingestion.get('has_active_chunk_set'):
        if ingestion.get('active_chunk_set_isolation_ready') and ingestion.get('active_chunk_set_embedding_model_matches'):
            _persist_publication(lesson, PUBLICATION_STATUS_READY, True, '')
            return
        _persist_publication(lesson, PUBLICATION_STATUS_PROCESSING, False, '')
        return

    if ingestion.get('latest_failed_job'):
        failed = ingestion['latest_failed_job']
        _persist_publication(
            lesson,
            PUBLICATION_STATUS_FAILED,
            False,
            failed.get('error_message') or 'Ingestion failed.',
        )
        return

    _persist_publication(lesson, PUBLICATION_STATUS_PROCESSING, False, '')
