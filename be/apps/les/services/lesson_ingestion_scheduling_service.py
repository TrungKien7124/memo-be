import hashlib
import json

from apps.app_server.models.lesson_model import LESSON_TYPE_LESSON
from apps.les.models import (
    LessonIngestionJob,
    LessonIngestionJobStatus,
    LessonIngestionJobType,
    LessonIngestionTriggerSource,
)


def _get_value(obj, key, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def is_ingestion_supported_lesson(lesson) -> bool:
    lesson_type = _get_value(lesson, 'lesson_type')
    return lesson_type == LESSON_TYPE_LESSON


def extract_ingestion_relevant_fields(lesson):
    return {
        'lesson_type': _get_value(lesson, 'lesson_type', None),
        'content_markdown': _get_value(lesson, 'content_markdown', '') or '',
        'video_url': _get_value(lesson, 'video_url', '') or '',
        'title': _get_value(lesson, 'title', '') or '',
    }


def build_lesson_source_version(lesson) -> str:
    payload = extract_ingestion_relevant_fields(lesson)
    normalized = json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()[:64]


def create_ingestion_job(lesson, job_type, trigger_source, source_version: str) -> LessonIngestionJob:
    return LessonIngestionJob.objects.create(
        lesson=lesson,
        job_type=job_type,
        trigger_source=trigger_source,
        status=LessonIngestionJobStatus.PENDING,
        source_version=source_version,
    )


def _enqueue_job_processing(job: LessonIngestionJob) -> None:
    # Local import to avoid circular dependency: tasks imports orchestration only.
    from apps.les.tasks import process_lesson_ingestion_job

    process_lesson_ingestion_job.delay(job.id)


def schedule_lesson_ingestion(lesson, trigger_source, job_type=None) -> LessonIngestionJob | None:
    if not is_ingestion_supported_lesson(lesson):
        return None

    resolved_job_type = job_type or LessonIngestionJobType.INGEST
    source_version = build_lesson_source_version(lesson)
    job = create_ingestion_job(
        lesson=lesson,
        job_type=resolved_job_type,
        trigger_source=trigger_source,
        source_version=source_version,
    )
    _enqueue_job_processing(job)
    return job


def schedule_lesson_reingestion_if_needed(previous_lesson_state, lesson) -> LessonIngestionJob | None:
    previous_supported = is_ingestion_supported_lesson(previous_lesson_state)
    current_supported = is_ingestion_supported_lesson(lesson)

    # supported -> unsupported: delete index
    if previous_supported and not current_supported:
        return schedule_lesson_index_delete(
            lesson,
            trigger_source=LessonIngestionTriggerSource.LESSON_UPDATED,
            require_supported_current=False,
        )

    # unsupported -> supported: ingest
    if not previous_supported and current_supported:
        return schedule_lesson_ingestion(
            lesson,
            trigger_source=LessonIngestionTriggerSource.LESSON_UPDATED,
            job_type=LessonIngestionJobType.INGEST,
        )

    # both unsupported: no ingestion jobs
    if not previous_supported and not current_supported:
        return None

    # supported -> supported: reingest only if ingestion-relevant fields changed
    previous_fields = extract_ingestion_relevant_fields(previous_lesson_state)
    current_fields = extract_ingestion_relevant_fields(lesson)

    if previous_fields == current_fields:
        return None

    return schedule_lesson_ingestion(
        lesson,
        trigger_source=LessonIngestionTriggerSource.LESSON_UPDATED,
        job_type=LessonIngestionJobType.REINGEST,
    )


def schedule_lesson_index_delete(
    lesson,
    trigger_source,
    require_supported_current: bool = True,
) -> LessonIngestionJob | None:
    if require_supported_current and not is_ingestion_supported_lesson(lesson):
        return None

    source_version = build_lesson_source_version(lesson)
    job = create_ingestion_job(
        lesson=lesson,
        job_type=LessonIngestionJobType.DELETE_INDEX,
        trigger_source=trigger_source,
        source_version=source_version,
    )
    _enqueue_job_processing(job)
    return job

