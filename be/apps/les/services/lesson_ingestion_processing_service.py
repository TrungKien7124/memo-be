import hashlib
import re
from typing import Any

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.ai.services.rag.retriever import delete_documents, index_documents
from apps.app_server.models.lesson_model import LESSON_TYPE_TEXT, LESSON_TYPE_VIDEO
from apps.les.models import (
    LessonContentChunk,
    LessonIngestionJob,
    LessonIngestionJobStatus,
    LessonIngestionJobType,
    LessonSourceDocument,
)


class LessonIngestionProcessingError(Exception):
    def __init__(self, message: str, error_payload: dict[str, Any] | None = None):
        super().__init__(message)
        self.error_payload = error_payload or {}


def _normalize_markdown_to_plain_text(markdown: str) -> str:
    if not markdown:
        return ''

    text = markdown.replace('\r\n', '\n')
    # Headings: "# Title" -> "Title" (keep as its own line)
    text = re.sub(r'^(#{1,6})\s+(.+)$', r'\2', text, flags=re.MULTILINE)
    # Links: "[label](url)" -> "label"
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    # Remove emphasis markers
    text = text.replace('*', '').replace('_', '')
    # Remove inline code backticks
    text = text.replace('`', '')
    # Strip blockquote markers
    text = re.sub(r'^\s*>\s?', '', text, flags=re.MULTILINE)
    # Strip list markers
    text = re.sub(r'^\s*[-*]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)
    # Normalize whitespace but keep paragraph boundaries
    text = text.strip()
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text


def normalize_lesson_text(raw_text: str) -> str:
    # Keep this deterministic and library-free for Sprint 2.
    return _normalize_markdown_to_plain_text(raw_text)


def get_video_transcript_from_url(video_url: str) -> str:
    """
    Boundary for transcript acquisition.

    Phase 1 behavior: transcript acquisition is not production-ready yet and must fail explicitly.
    Tests will patch this function.
    """

    raise LessonIngestionProcessingError(
        'Transcript acquisition is not available for this environment.',
        error_payload={'video_url': video_url, 'error': 'transcript_unavailable'},
    )


def extract_source_document_for_lesson(lesson, job: LessonIngestionJob) -> LessonSourceDocument:
    lesson_type = getattr(lesson, 'lesson_type', None)
    lesson_id = getattr(lesson, 'id', None)

    if lesson_type == LESSON_TYPE_TEXT:
        raw_text = getattr(lesson, 'content_markdown', '') or ''
        normalized_text = normalize_lesson_text(raw_text)
        if not normalized_text:
            raise LessonIngestionProcessingError(
                'Text extraction produced empty content.',
                error_payload={'lesson_id': str(lesson_id), 'source_type': 'text_markdown'},
            )

        checksum = hashlib.sha256(normalized_text.encode('utf-8')).hexdigest()
        return LessonSourceDocument.objects.create(
            lesson=lesson,
            ingestion_job=job,
            source_type='text_markdown',
            source_locator=f'lesson:{lesson_id}:content_markdown',
            raw_text=raw_text,
            normalized_text=normalized_text,
            language_code='en',
            checksum=checksum,
            metadata_json={
                'lesson_id': str(lesson_id),
                'job_type': job.job_type,
                'trigger_source': job.trigger_source,
            },
        )

    if lesson_type == LESSON_TYPE_VIDEO:
        video_url = getattr(lesson, 'video_url', '') or ''
        if not video_url:
            raise LessonIngestionProcessingError(
                'Video lesson has an empty video_url.',
                error_payload={'lesson_id': str(lesson_id), 'source_type': 'video_url_transcript'},
            )

        transcript = get_video_transcript_from_url(video_url)
        if not transcript:
            raise LessonIngestionProcessingError(
                'Transcript acquisition returned empty transcript.',
                error_payload={'lesson_id': str(lesson_id), 'video_url': video_url},
            )

        normalized_text = normalize_lesson_text(transcript)
        checksum = hashlib.sha256(normalized_text.encode('utf-8')).hexdigest()
        return LessonSourceDocument.objects.create(
            lesson=lesson,
            ingestion_job=job,
            source_type='video_url_transcript',
            source_locator=video_url,
            raw_text=transcript,
            normalized_text=normalized_text,
            language_code='en',
            checksum=checksum,
            metadata_json={
                'lesson_id': str(lesson_id),
                'job_type': job.job_type,
                'trigger_source': job.trigger_source,
            },
        )

    raise LessonIngestionProcessingError(
        'Unsupported lesson type for ingestion processing.',
        error_payload={'lesson_id': str(lesson_id), 'lesson_type': lesson_type},
    )


def chunk_normalized_text(normalized_text: str, target_chars: int = 3500):
    if not normalized_text:
        return []

    # Prefer paragraph boundaries first.
    raw_paragraphs = [p.strip() for p in normalized_text.split('\n\n') if p.strip()]
    if not raw_paragraphs:
        raw_paragraphs = [normalized_text.strip()]

    joiner = '\n\n'
    chunks: list[dict[str, Any]] = []

    cursor = 0
    current_paragraphs: list[str] = []
    current_len = 0

    def _finalize_chunk():
        nonlocal cursor, current_paragraphs, current_len
        if not current_paragraphs:
            return

        content = joiner.join(current_paragraphs).strip()
        if not content:
            current_paragraphs = []
            current_len = 0
            return

        start = cursor
        end = start + len(content)
        token_estimate = max(1, int(round(len(content) / 4)))
        chunks.append(
            {
                'content': content,
                'char_start': start,
                'char_end': end,
                'token_estimate': token_estimate,
            }
        )
        cursor = end + len(joiner)
        current_paragraphs = []
        current_len = 0

    for para in raw_paragraphs:
        para_len = len(para)
        candidate_len = para_len if not current_paragraphs else current_len + len(joiner) + para_len

        if current_paragraphs and candidate_len > target_chars:
            _finalize_chunk()

        if not current_paragraphs:
            current_paragraphs = [para]
            current_len = para_len
        else:
            current_paragraphs.append(para)
            current_len = candidate_len

    _finalize_chunk()

    # Avoid empty or trivially small chunks.
    return [chunk for chunk in chunks if chunk['content'].strip()]


def build_chunk_metadata(lesson, source_type: str, chunk_index: int) -> dict[str, str | int]:
    module = lesson.module
    return {
        'lesson_id': str(lesson.id),
        'module_id': str(module.id),
        'course_id': str(module.course_id),
        'lesson_type': lesson.lesson_type,
        'source_type': source_type,
        'chunk_index': chunk_index,
    }


def persist_chunk_set(lesson, job: LessonIngestionJob, source_document: LessonSourceDocument, chunks) -> list[LessonContentChunk]:
    embedding_provider = 'ollama'
    embedding_model = getattr(settings, 'AI_OLLAMA_EMBED_MODEL', 'nomic-embed-text')

    persisted: list[LessonContentChunk] = []
    for idx, chunk in enumerate(chunks):
        metadata = build_chunk_metadata(lesson, source_document.source_type, idx)

        obj = LessonContentChunk.objects.create(
            lesson=lesson,
            ingestion_job=job,
            source_document=source_document,
            chunk_index=idx,
            content=chunk['content'],
            token_estimate=chunk['token_estimate'],
            char_start=chunk['char_start'],
            char_end=chunk['char_end'],
            vector_document_id='',
            embedding_provider=embedding_provider,
            embedding_model=embedding_model,
            metadata_json={
                **metadata,
                'ingestion_job_id': str(job.id),
            },
            is_active=False,
        )
        persisted.append(obj)

    return persisted


def index_chunks_and_persist_vector_ids(chunks: list[LessonContentChunk]) -> None:
    if not chunks:
        raise LessonIngestionProcessingError('No chunks were created to index.')

    documents = [c.content for c in chunks]
    metadatas = [c.metadata_json for c in chunks]

    vector_document_ids = index_documents(documents, metadatas=metadatas)
    if not vector_document_ids:
        rag_enabled = getattr(settings, 'AI_RAG_ENABLED', False)
        if not rag_enabled:
            raise LessonIngestionProcessingError(
                'RAG vector indexing is disabled (AI_RAG_ENABLED=false). Enable RAG to complete ingestion indexing.',
                error_payload={
                    'stage': 'index_documents',
                    'rag_enabled': rag_enabled,
                    'vector_store': getattr(settings, 'AI_VECTOR_STORE', 'chroma'),
                    'chunks': len(chunks),
                    'returned_ids': 0,
                },
            )

        raise LessonIngestionProcessingError(
            'Vector store indexing returned no document IDs.',
            error_payload={'stage': 'index_documents', 'chunks': len(chunks), 'returned_ids': 0},
        )

    if len(vector_document_ids) != len(chunks):
        raise LessonIngestionProcessingError(
            'Vector store indexing returned mismatched ID count.',
            error_payload={'chunks': len(chunks), 'returned_ids': len(vector_document_ids)},
        )

    for chunk_obj, vector_id in zip(chunks, vector_document_ids):
        chunk_obj.vector_document_id = str(vector_id)
        chunk_obj.save(update_fields=['vector_document_id', 'updated_at'])


def activate_chunk_set(lesson, new_chunks: list[LessonContentChunk]) -> None:
    if not new_chunks:
        raise LessonIngestionProcessingError('No chunk set to activate.')

    old_active_qs = LessonContentChunk.objects.filter(lesson=lesson, is_active=True)
    old_active_ids = list(old_active_qs.values_list('id', flat=True))
    old_vector_ids = list(
        old_active_qs.exclude(vector_document_id='').values_list('vector_document_id', flat=True)
    )
    new_vector_ids = [
        str(c.vector_document_id)
        for c in new_chunks
        if getattr(c, 'vector_document_id', '') and str(c.vector_document_id).strip()
    ]

    new_ids = [c.id for c in new_chunks]
    with transaction.atomic():
        LessonContentChunk.objects.filter(lesson=lesson, is_active=True).update(is_active=False)
        LessonContentChunk.objects.filter(id__in=new_ids).update(is_active=True)

    if old_vector_ids:
        deleted = delete_documents(old_vector_ids)
        if not deleted:
            deleted_new = False
            if new_vector_ids:
                deleted_new = delete_documents(new_vector_ids)

            rollback_applied = False
            with transaction.atomic():
                LessonContentChunk.objects.filter(id__in=new_ids).update(is_active=False)
                if old_active_ids:
                    LessonContentChunk.objects.filter(id__in=old_active_ids).update(is_active=True)
                rollback_applied = True
            raise LessonIngestionProcessingError(
                'Failed to delete stale vector documents after activating new chunk set.',
                error_payload={
                    'stage': 'delete_stale_vectors',
                    'lesson_id': str(lesson.id),
                    'stale_vector_count': len(old_vector_ids),
                    'rollback_applied': rollback_applied,
                    'deleted_new_vector_set': deleted_new,
                },
            )


def orchestrate_lesson_ingestion_job(job: LessonIngestionJob) -> None:
    """
    Real ingestion orchestration for Sprint 2/3 (text + video transcript boundary + chunk/index persistence).
    """

    lesson = job.lesson

    if job.job_type == LessonIngestionJobType.DELETE_INDEX:
        active_qs = LessonContentChunk.objects.filter(lesson=lesson, is_active=True)
        active_vector_ids = list(
            active_qs
            .exclude(vector_document_id='')
            .values_list('vector_document_id', flat=True)
        )
        if active_vector_ids:
            deleted = delete_documents(active_vector_ids)
            if not deleted:
                raise LessonIngestionProcessingError(
                    'Failed to delete vectors during delete_index job.',
                    error_payload={
                        'stage': 'delete_index_vectors',
                        'lesson_id': str(lesson.id),
                        'active_vector_count': len(active_vector_ids),
                    },
                )
        active_qs.update(is_active=False)
        return

    if job.job_type not in (LessonIngestionJobType.INGEST, LessonIngestionJobType.REINGEST):
        raise LessonIngestionProcessingError(
            'Unsupported job_type for this processing step.',
            error_payload={'job_id': str(job.id), 'job_type': job.job_type},
        )

    source_document = extract_source_document_for_lesson(lesson, job)
    chunks = chunk_normalized_text(source_document.normalized_text)
    if not chunks:
        raise LessonIngestionProcessingError(
            'Chunk generation produced no usable chunks.',
            error_payload={'lesson_id': str(lesson.id), 'source_type': source_document.source_type},
        )

    persisted_chunks = persist_chunk_set(lesson, job, source_document, chunks)

    # Index first; on failure we do NOT deactivate previous active chunks.
    index_chunks_and_persist_vector_ids(persisted_chunks)

    # Activation happens only after successful vector_document_id persistence.
    activate_chunk_set(lesson, persisted_chunks)


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

