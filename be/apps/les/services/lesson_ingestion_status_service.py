from __future__ import annotations

from collections import defaultdict
from typing import Any

from django.conf import settings

from apps.app_server.models.lesson_model import (
    Lesson,
    PUBLICATION_STATUS_FAILED,
    PUBLICATION_STATUS_PROCESSING,
    TRANSCRIPT_STATUS_FAILED,
)
from apps.les.models import LessonContentChunk, LessonIngestionJob, LessonIngestionJobStatus
from apps.les.services.lesson_ingestion_scheduling_service import is_ingestion_supported_lesson

LESSON_PIPELINE_STATUS_BATCH_MAX_IDS = 100


def _expected_embedding_model() -> str:
    vector_store = getattr(settings, 'AI_VECTOR_STORE', 'pgvector')
    if vector_store == 'chroma':
        return getattr(settings, 'AI_OLLAMA_EMBED_MODEL', 'nomic-embed-text')
    return getattr(settings, 'AI_GEMINI_EMBED_MODEL', 'gemini-embedding-001')


def _job_finished_sort_key(job: LessonIngestionJob) -> tuple:
    return (
        job.finished_at is not None,
        job.finished_at or job.created_at,
        job.created_at,
    )


def _lesson_ingestion_status_core(
    lesson: Lesson,
    active_chunks: list[dict[str, Any]],
    jobs_desc: list[LessonIngestionJob],
) -> dict:
    supported_for_ingestion = is_ingestion_supported_lesson(lesson)
    active_chunk_count = len(active_chunks)
    has_active_chunk_set = active_chunk_count > 0
    expected_embedding_model = _expected_embedding_model()

    active_chunk_set_has_ingestion_job_id_metadata = all(
        bool(chunk['metadata_json'] and chunk['metadata_json'].get('ingestion_job_id'))
        for chunk in active_chunks
    )
    active_chunk_set_isolation_ready = (
        active_chunk_set_has_ingestion_job_id_metadata
        and len(
            {
                chunk['metadata_json'].get('ingestion_job_id')
                for chunk in active_chunks
                if chunk['metadata_json']
            },
        )
        == 1
    )
    active_chunk_set_embedding_model_matches = all(
        chunk.get('embedding_model') == expected_embedding_model
        for chunk in active_chunks
    )

    latest_job = jobs_desc[0] if jobs_desc else None

    completed_jobs = [j for j in jobs_desc if j.status == LessonIngestionJobStatus.COMPLETED]
    latest_completed_job = max(completed_jobs, key=_job_finished_sort_key) if completed_jobs else None

    failed_jobs = [j for j in jobs_desc if j.status == LessonIngestionJobStatus.FAILED]
    latest_failed_job = max(failed_jobs, key=_job_finished_sort_key) if failed_jobs else None

    active_job_db_ids = {chunk['ingestion_job_id'] for chunk in active_chunks}
    candidates_active = [
        j for j in jobs_desc
        if j.status == LessonIngestionJobStatus.COMPLETED and j.id in active_job_db_ids
    ]
    latest_active_completed_job = (
        max(candidates_active, key=_job_finished_sort_key) if candidates_active else None
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
        'active_chunk_set_isolation_ready': active_chunk_set_isolation_ready,
        'active_chunk_set_embedding_model_matches': active_chunk_set_embedding_model_matches,
        'last_indexed_at': last_indexed_at,
    }


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
    active_chunks_qs = LessonContentChunk.objects.filter(lesson=lesson, is_active=True)
    active_chunks = list(
        active_chunks_qs.values('embedding_model', 'metadata_json', 'ingestion_job_id'),
    )
    jobs_desc = list(
        LessonIngestionJob.objects.filter(lesson=lesson).order_by('-created_at'),
    )
    return _lesson_ingestion_status_core(lesson, active_chunks, jobs_desc)


def _admin_publication_overlay(lesson: Lesson, base: dict) -> dict:
    merged = dict(base)
    publication_status = lesson.publication_status
    is_active = lesson.is_active
    publication_error = lesson.publication_error
    if publication_status == PUBLICATION_STATUS_PROCESSING:
        latest_job = base.get('latest_job') or {}
        latest_failed_job = base.get('latest_failed_job') or {}
        if lesson.transcript_status == TRANSCRIPT_STATUS_FAILED:
            publication_status = PUBLICATION_STATUS_FAILED
            is_active = False
            publication_error = lesson.transcript_error or 'Transcript failed.'
        elif (
            latest_job.get('status') == LessonIngestionJobStatus.FAILED
            and not base.get('has_active_chunk_set')
        ):
            publication_status = PUBLICATION_STATUS_FAILED
            is_active = False
            publication_error = latest_failed_job.get('error_message') or 'Ingestion failed.'
    merged['publication_status'] = publication_status
    merged['is_active'] = is_active
    merged['publication_error'] = publication_error
    merged['transcript_status'] = lesson.transcript_status
    merged['transcript_error'] = lesson.transcript_error
    return merged


def get_admin_lesson_pipeline_status(lesson: Lesson) -> dict:
    """
    Admin-only pipeline snapshot, read-only.
    """
    lesson.refresh_from_db()
    payload = get_lesson_ingestion_status(lesson)
    return _admin_publication_overlay(lesson, payload)


def get_admin_lesson_pipeline_status_batch(ordered_lesson_ids: list) -> dict:
    """
    Admin-only pipeline snapshots for many lessons in one read-only pass.

    Args:
        ordered_lesson_ids: UUID primary keys in response order (already validated and deduped).

    Returns:
        dict with:
            records: list of payloads matching single-lesson admin status shape, in input order
            missing_lesson_ids: string UUIDs from the input that have no Lesson row
    """
    if not ordered_lesson_ids:
        return {'records': [], 'missing_lesson_ids': []}

    lessons_by_id = Lesson.objects.in_bulk(ordered_lesson_ids, field_name='id')
    missing_lesson_ids = [str(uid) for uid in ordered_lesson_ids if uid not in lessons_by_id]

    existing_ids = [uid for uid in ordered_lesson_ids if uid in lessons_by_id]
    if not existing_ids:
        return {'records': [], 'missing_lesson_ids': missing_lesson_ids}

    chunk_rows = list(
        LessonContentChunk.objects.filter(
            lesson_id__in=existing_ids,
            is_active=True,
        ).values('lesson_id', 'embedding_model', 'metadata_json', 'ingestion_job_id'),
    )
    chunks_by_lesson: dict = defaultdict(list)
    for row in chunk_rows:
        chunks_by_lesson[row['lesson_id']].append(row)

    all_jobs = list(
        LessonIngestionJob.objects.filter(lesson_id__in=existing_ids).order_by('-created_at'),
    )
    jobs_by_lesson: dict = defaultdict(list)
    for job in all_jobs:
        jobs_by_lesson[job.lesson_id].append(job)

    records = []
    for lesson_id in ordered_lesson_ids:
        if lesson_id not in lessons_by_id:
            continue
        lesson = lessons_by_id[lesson_id]
        core = _lesson_ingestion_status_core(
            lesson,
            chunks_by_lesson[lesson_id],
            jobs_by_lesson[lesson_id],
        )
        records.append(_admin_publication_overlay(lesson, core))

    return {'records': records, 'missing_lesson_ids': missing_lesson_ids}
