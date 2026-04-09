from unittest.mock import patch

from django.test import TestCase

from rest_framework import status
from rest_framework.test import APITestCase

from apps.ai.services.rag import retriever
from apps.app_server.models.course_model import Course, COURSE_STATUS_PUBLISHED
from apps.app_server.models.lesson_model import (
    LESSON_TYPE_QUIZ,
    LESSON_TYPE_TEXT,
    LESSON_TYPE_VIDEO,
    Lesson,
)
from apps.app_server.models.module_model import Module
from apps.app_server.models.user_model import ROLE_STUDENT, ROLE_TEACHER, User
from apps.les.models import (
    LessonContentChunk,
    LessonIngestionJob,
    LessonIngestionJobStatus,
    LessonIngestionJobType,
    LessonIngestionTriggerSource,
    LessonSourceDocument,
)
from apps.les.services.lesson_ingestion_processing_service import LessonIngestionProcessingError
from apps.les.tasks import process_lesson_ingestion_job


class LessonIngestionProcessingAPITestCase(TestCase):
    def setUp(self):
        self.teacher_password = 'Password@123'
        self.teacher = User.objects.create_user(
            email='teacher-ingestion@example.com',
            username='teacher-ingestion',
            password=self.teacher_password,
            role=ROLE_TEACHER,
        )
        self.course = Course.objects.create(
            title='Ingestion Processing Course',
            description='Course for ingestion processing tests',
            status=COURSE_STATUS_PUBLISHED,
            created_by=self.teacher,
        )
        self.module = Module.objects.create(
            course=self.course,
            title='Module 1',
            order_index=1,
        )

    def _create_text_lesson(self, **overrides):
        return Lesson.objects.create(
            module=self.module,
            title=overrides.get('title', 'Text Lesson'),
            lesson_type=LESSON_TYPE_TEXT,
            content_markdown=overrides.get('content_markdown', 'Hello world'),
            video_url='',
            quiz_questions=[],
            is_final=False,
            min_watch_time=10,
            order_index=1,
        )

    def _create_video_lesson(self, **overrides):
        return Lesson.objects.create(
            module=self.module,
            title=overrides.get('title', 'Video Lesson'),
            lesson_type=LESSON_TYPE_VIDEO,
            content_markdown='',
            video_url=overrides.get('video_url', 'https://example.com/video.mp4'),
            quiz_questions=[],
            is_final=False,
            min_watch_time=10,
            order_index=1,
        )

    def _seed_active_chunk_set(self, lesson, job, *, source_type: str, normalized_text: str):
        source_document = LessonSourceDocument.objects.create(
            lesson=lesson,
            ingestion_job=job,
            source_type=source_type,
            source_locator='seed',
            raw_text=normalized_text,
            normalized_text=normalized_text,
            language_code='en',
            checksum='seed-checksum',
            metadata_json={'seed': True},
        )

        metadata_json = {
            'lesson_id': str(lesson.id),
            'module_id': str(lesson.module.id),
            'course_id': str(lesson.module.course_id),
            'lesson_type': lesson.lesson_type,
            'source_type': source_type,
            'chunk_index': 0,
            'ingestion_job_id': str(job.id),
        }

        chunk = LessonContentChunk.objects.create(
            lesson=lesson,
            ingestion_job=job,
            source_document=source_document,
            chunk_index=0,
            content=normalized_text,
            token_estimate=1,
            char_start=0,
            char_end=len(normalized_text),
            vector_document_id='seed-vector-id',
            embedding_provider='gemini',
            embedding_model='gemini-embedding-001',
            metadata_json=metadata_json,
            is_active=True,
        )
        return source_document, chunk

    def _build_ingestion_job(self, lesson, *, job_type, trigger_source, status=LessonIngestionJobStatus.PENDING):
        return LessonIngestionJob.objects.create(
            lesson=lesson,
            job_type=job_type,
            trigger_source=trigger_source,
            status=status,
            source_version='v1',
        )

    @patch('apps.les.services.lesson_ingestion_processing_service.index_documents')
    def test_text_ingestion_job_creates_source_docs_and_chunks_and_activates(self, mock_index_documents):
        def _fake_index_documents(documents, metadatas=None):
            return [f'vec-{i}' for i in range(len(documents))]

        mock_index_documents.side_effect = _fake_index_documents

        lesson = self._create_text_lesson()
        job = self._build_ingestion_job(
            lesson,
            job_type=LessonIngestionJobType.INGEST,
            trigger_source=LessonIngestionTriggerSource.LESSON_CREATED,
        )

        process_lesson_ingestion_job.run(str(job.id))
        job.refresh_from_db()

        self.assertEqual(job.status, LessonIngestionJobStatus.COMPLETED)
        self.assertIsNotNone(job.started_at)
        self.assertIsNotNone(job.finished_at)

        source_docs = LessonSourceDocument.objects.filter(lesson=lesson, ingestion_job=job)
        self.assertEqual(source_docs.count(), 1)

        chunks = LessonContentChunk.objects.filter(lesson=lesson, ingestion_job=job)
        self.assertGreaterEqual(chunks.count(), 1)

        active_chunks = chunks.filter(is_active=True)
        self.assertEqual(active_chunks.count(), chunks.count())

        for chunk in chunks:
            self.assertTrue(chunk.vector_document_id)

    @patch('apps.les.services.lesson_ingestion_processing_service.get_video_transcript_from_url')
    def test_video_transcript_failure_marks_job_failed_and_keeps_previous_active_set(self, mock_transcript):
        lesson = self._create_video_lesson()

        prev_job = self._build_ingestion_job(
            lesson,
            job_type=LessonIngestionJobType.INGEST,
            trigger_source=LessonIngestionTriggerSource.LESSON_CREATED,
            status=LessonIngestionJobStatus.COMPLETED,
        )
        _, prev_chunk = self._seed_active_chunk_set(
            lesson,
            prev_job,
            source_type='video_url_transcript',
            normalized_text='previous active transcript chunk',
        )

        pending_job = self._build_ingestion_job(
            lesson,
            job_type=LessonIngestionJobType.INGEST,
            trigger_source=LessonIngestionTriggerSource.LESSON_CREATED,
            status=LessonIngestionJobStatus.PENDING,
        )

        mock_transcript.side_effect = LessonIngestionProcessingError(
            'Transcript unavailable',
            error_payload={'video_url': lesson.video_url, 'reason': 'provider_unavailable'},
        )

        process_lesson_ingestion_job.run(str(pending_job.id))
        pending_job.refresh_from_db()

        self.assertEqual(pending_job.status, LessonIngestionJobStatus.FAILED)
        self.assertIn('Transcript unavailable', pending_job.error_message)
        self.assertEqual(pending_job.error_payload.get('video_url'), lesson.video_url)

        # Previous active set remains active.
        prev_chunk.refresh_from_db()
        self.assertTrue(prev_chunk.is_active)

        # New source document must not be created when transcript acquisition fails.
        self.assertEqual(
            LessonSourceDocument.objects.filter(lesson=lesson, ingestion_job=pending_job).count(),
            0,
        )
        self.assertEqual(
            LessonContentChunk.objects.filter(lesson=lesson, ingestion_job=pending_job).count(),
            0,
        )

    @patch(
        'apps.les.services.lesson_ingestion_processing_service.delete_documents',
        return_value=True,
    )
    @patch('apps.les.services.lesson_ingestion_processing_service.index_documents')
    def test_reingest_swaps_active_chunk_set_after_success(
        self, mock_index_documents, _mock_delete_documents
    ):
        def _fake_index_documents(documents, metadatas=None):
            return [f'new-vec-{i}' for i in range(len(documents))]

        mock_index_documents.side_effect = _fake_index_documents

        lesson = self._create_text_lesson(title='Reingest Text Lesson', content_markdown='Initial content')
        prev_job = self._build_ingestion_job(
            lesson,
            job_type=LessonIngestionJobType.INGEST,
            trigger_source=LessonIngestionTriggerSource.LESSON_CREATED,
            status=LessonIngestionJobStatus.COMPLETED,
        )
        _, prev_chunk = self._seed_active_chunk_set(
            lesson,
            prev_job,
            source_type='text_markdown',
            normalized_text='previous active text',
        )

        reingest_job = self._build_ingestion_job(
            lesson,
            job_type=LessonIngestionJobType.REINGEST,
            trigger_source=LessonIngestionTriggerSource.LESSON_UPDATED,
            status=LessonIngestionJobStatus.PENDING,
        )

        process_lesson_ingestion_job.run(str(reingest_job.id))
        reingest_job.refresh_from_db()

        self.assertEqual(reingest_job.status, LessonIngestionJobStatus.COMPLETED)

        prev_chunk.refresh_from_db()
        self.assertFalse(prev_chunk.is_active)

        new_chunks = LessonContentChunk.objects.filter(lesson=lesson, ingestion_job=reingest_job)
        self.assertGreaterEqual(new_chunks.count(), 1)
        self.assertTrue(new_chunks.filter(is_active=True).exists())
        self.assertEqual(new_chunks.filter(is_active=True).count(), new_chunks.count())

    @patch('apps.les.services.lesson_ingestion_processing_service.index_documents')
    def test_indexing_failure_marks_job_failed_and_keeps_previous_active_set(self, mock_index_documents):
        lesson = self._create_text_lesson(title='Indexing Failure Lesson', content_markdown='Some text')

        prev_job = self._build_ingestion_job(
            lesson,
            job_type=LessonIngestionJobType.INGEST,
            trigger_source=LessonIngestionTriggerSource.LESSON_CREATED,
            status=LessonIngestionJobStatus.COMPLETED,
        )
        _, prev_chunk = self._seed_active_chunk_set(
            lesson,
            prev_job,
            source_type='text_markdown',
            normalized_text='previous active before indexing failure',
        )

        new_job = self._build_ingestion_job(
            lesson,
            job_type=LessonIngestionJobType.INGEST,
            trigger_source=LessonIngestionTriggerSource.LESSON_CREATED,
            status=LessonIngestionJobStatus.PENDING,
        )

        mock_index_documents.side_effect = LessonIngestionProcessingError(
            'Vector store indexing failed',
            error_payload={'stage': 'index_documents'},
        )

        process_lesson_ingestion_job.run(str(new_job.id))
        new_job.refresh_from_db()

        self.assertEqual(new_job.status, LessonIngestionJobStatus.FAILED)
        self.assertIn('Vector store indexing failed', new_job.error_message)
        self.assertEqual(new_job.error_payload.get('stage'), 'index_documents')

        prev_chunk.refresh_from_db()
        self.assertTrue(prev_chunk.is_active)

        new_chunks = LessonContentChunk.objects.filter(lesson=lesson, ingestion_job=new_job)
        self.assertGreaterEqual(new_chunks.count(), 1)
        self.assertEqual(new_chunks.filter(is_active=True).count(), 0)


class LessonIngestionStatusEndpointsAPITestCase(APITestCase):
    def setUp(self):
        self.teacher_password = 'Password@123'
        self.teacher = User.objects.create_user(
            email='teacher-status@example.com',
            username='teacher-status',
            password=self.teacher_password,
            role=ROLE_TEACHER,
        )
        self.learner = User.objects.create_user(
            email='learner-status@example.com',
            username='learner-status',
            password=self.teacher_password,
            role=ROLE_STUDENT,
        )

        self.course = Course.objects.create(
            title='Ingestion Status Course',
            description='Course for ingestion status endpoints tests',
            status=COURSE_STATUS_PUBLISHED,
            created_by=self.teacher,
        )
        self.module = Module.objects.create(
            course=self.course,
            title='Module 1',
            order_index=1,
        )

    def _create_text_lesson(self, **overrides):
        return Lesson.objects.create(
            module=self.module,
            title=overrides.get('title', 'Text Lesson'),
            lesson_type=LESSON_TYPE_TEXT,
            content_markdown=overrides.get('content_markdown', 'hello world'),
            video_url='',
            quiz_questions=[],
            is_final=False,
            min_watch_time=10,
            order_index=1,
        )

    def _create_video_lesson(self, **overrides):
        return Lesson.objects.create(
            module=self.module,
            title=overrides.get('title', 'Video Lesson'),
            lesson_type=LESSON_TYPE_VIDEO,
            content_markdown='',
            video_url=overrides.get('video_url', 'https://example.com/video.mp4'),
            quiz_questions=[],
            is_final=False,
            min_watch_time=10,
            order_index=1,
        )

    def _create_quiz_lesson(self, **overrides):
        return Lesson.objects.create(
            module=self.module,
            title=overrides.get('title', 'Quiz Lesson'),
            lesson_type=LESSON_TYPE_QUIZ,
            content_markdown='',
            video_url='',
            quiz_questions=overrides.get(
                'quiz_questions',
                [],
            ),
            is_final=False,
            min_watch_time=10,
            order_index=1,
        )

    def _seed_active_chunk_set(self, lesson, *, source_type: str = 'text_markdown'):
        # Use explicit finished_at so status aggregation can compute last_indexed_at.
        job_finished_at = self._now_minus(seconds=3600)
        job_started_at = self._now_minus(seconds=7200)

        ingestion_job = LessonIngestionJob.objects.create(
            lesson=lesson,
            job_type=LessonIngestionJobType.INGEST,
            trigger_source=LessonIngestionTriggerSource.LESSON_CREATED,
            status=LessonIngestionJobStatus.COMPLETED,
            source_version='v1',
            started_at=job_started_at,
            finished_at=job_finished_at,
        )

        source_document = LessonSourceDocument.objects.create(
            lesson=lesson,
            ingestion_job=ingestion_job,
            source_type=source_type,
            source_locator='seed',
            raw_text='seed raw',
            normalized_text='seed normalized',
            language_code='en',
            checksum='seed-checksum',
            metadata_json={'seed': True},
        )

        normalized_text = 'seed normalized'
        chunk = LessonContentChunk.objects.create(
            lesson=lesson,
            ingestion_job=ingestion_job,
            source_document=source_document,
            chunk_index=0,
            content=normalized_text,
            token_estimate=1,
            char_start=0,
            char_end=len(normalized_text),
            vector_document_id='seed-vector-id',
            embedding_provider='gemini',
            embedding_model='gemini-embedding-001',
            metadata_json={
                'lesson_id': str(lesson.id),
                'module_id': str(lesson.module.id),
                'course_id': str(lesson.module.course_id),
                'lesson_type': lesson.lesson_type,
                'source_type': source_type,
                'chunk_index': 0,
                'ingestion_job_id': str(ingestion_job.id),
            },
            is_active=True,
        )
        return ingestion_job, source_document, chunk

    def _now_minus(self, *, seconds: int):
        from django.utils import timezone
        from datetime import timedelta

        return timezone.now() - timedelta(seconds=seconds)

    def test_job_list_response_includes_core_fields(self):
        self.client.force_authenticate(user=self.teacher)

        lesson = self._create_text_lesson()
        job1 = LessonIngestionJob.objects.create(
            lesson=lesson,
            job_type=LessonIngestionJobType.INGEST,
            trigger_source=LessonIngestionTriggerSource.LESSON_CREATED,
            status=LessonIngestionJobStatus.COMPLETED,
            source_version='v1',
        )
        job2 = LessonIngestionJob.objects.create(
            lesson=lesson,
            job_type=LessonIngestionJobType.REINGEST,
            trigger_source=LessonIngestionTriggerSource.LESSON_UPDATED,
            status=LessonIngestionJobStatus.PENDING,
            source_version='v2',
        )

        response = self.client.get('/api/lesson-ingestion/jobs/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'success')
        self.assertIn('records', response.data['data'])
        self.assertIn('pageinfo', response.data['data'])
        self.assertIsInstance(response.data['data']['records'], list)
        self.assertGreaterEqual(len(response.data['data']['records']), 2)

        item = response.data['data']['records'][0]
        for field in (
            'id',
            'lesson_id',
            'job_type',
            'trigger_source',
            'status',
            'source_version',
            'started_at',
            'finished_at',
            'created_at',
            'updated_at',
        ):
            self.assertIn(field, item)

        _ = (job1.id, job2.id)  # keep variables referenced for clarity

    def test_job_detail_response_includes_error_fields(self):
        self.client.force_authenticate(user=self.teacher)

        lesson = self._create_text_lesson()
        job = LessonIngestionJob.objects.create(
            lesson=lesson,
            job_type=LessonIngestionJobType.INGEST,
            trigger_source=LessonIngestionTriggerSource.LESSON_CREATED,
            status=LessonIngestionJobStatus.FAILED,
            source_version='v1',
            error_message='boom',
            error_payload={'stage': 'index_documents'},
        )

        response = self.client.get(f'/api/lesson-ingestion/jobs/{job.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('data', response.data)

        self.assertEqual(response.data['data']['id'], str(job.id))
        self.assertEqual(response.data['data']['error_message'], 'boom')
        self.assertEqual(response.data['data']['error_payload']['stage'], 'index_documents')

    def test_job_detail_unknown_job_returns_not_found(self):
        self.client.force_authenticate(user=self.teacher)

        from uuid import uuid4

        response = self.client.get(f'/api/lesson-ingestion/jobs/{uuid4()}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data['status'], 'warning')
        self.assertEqual(response.data['code'], 604)
        self.assertIn('message', response.data)

    def test_lesson_status_supported_with_active_chunk_set(self):
        self.client.force_authenticate(user=self.teacher)

        lesson = self._create_text_lesson(title='Status Text Lesson')
        completed_job, _, _ = self._seed_active_chunk_set(lesson, source_type='text_markdown')

        response = self.client.get(f'/api/lesson-ingestion/lessons/{lesson.id}/status/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.data['data']

        self.assertTrue(payload['supported_for_ingestion'])
        self.assertEqual(payload['lesson_type'], LESSON_TYPE_TEXT)
        self.assertEqual(payload['active_chunk_count'], 1)
        self.assertTrue(payload['has_active_chunk_set'])
        self.assertEqual(payload['latest_completed_job_id'], str(completed_job.id))
        self.assertIsNone(payload['latest_failed_job'])

    def test_lesson_status_supported_failed_latest_keeps_previous_active(self):
        self.client.force_authenticate(user=self.teacher)

        lesson = self._create_text_lesson(title='Status Failed Lesson')
        completed_job, _, _ = self._seed_active_chunk_set(lesson, source_type='text_markdown')

        failed_job = LessonIngestionJob.objects.create(
            lesson=lesson,
            job_type=LessonIngestionJobType.REINGEST,
            trigger_source=LessonIngestionTriggerSource.LESSON_UPDATED,
            status=LessonIngestionJobStatus.FAILED,
            source_version='v2',
            error_message='indexing failed',
            error_payload={'stage': 'index_documents'},
        )
        # Ensure the failed job is "latest" by created_at ordering.
        failed_job.finished_at = self._now_minus(seconds=10)
        failed_job.save(update_fields=['finished_at'])

        response = self.client.get(f'/api/lesson-ingestion/lessons/{lesson.id}/status/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.data['data']

        self.assertEqual(payload['active_chunk_count'], 1)
        self.assertTrue(payload['has_active_chunk_set'])
        self.assertEqual(payload['latest_completed_job_id'], str(completed_job.id))
        self.assertIsNotNone(payload['latest_failed_job'])
        self.assertEqual(payload['latest_failed_job']['id'], str(failed_job.id))

    def test_lesson_status_unsupported_quiz(self):
        self.client.force_authenticate(user=self.teacher)

        lesson = self._create_quiz_lesson()
        response = self.client.get(f'/api/lesson-ingestion/lessons/{lesson.id}/status/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        payload = response.data['data']
        self.assertFalse(payload['supported_for_ingestion'])
        self.assertEqual(payload['lesson_type'], LESSON_TYPE_QUIZ)
        self.assertEqual(payload['active_chunk_count'], 0)
        self.assertFalse(payload['has_active_chunk_set'])

    @patch('apps.les.tasks.process_lesson_ingestion_job.delay')
    def test_manual_reindex_text_creates_reingest_pending_job(self, mock_delay):
        self.client.force_authenticate(user=self.teacher)

        lesson = self._create_text_lesson(title='Manual Reindex Text')
        response = self.client.post(f'/api/lesson-ingestion/lessons/{lesson.id}/reindex/')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('data', response.data)

        job = LessonIngestionJob.objects.get(lesson=lesson, trigger_source=LessonIngestionTriggerSource.MANUAL_REINDEX)
        self.assertEqual(job.job_type, LessonIngestionJobType.REINGEST)
        self.assertEqual(job.status, LessonIngestionJobStatus.PENDING)
        self.assertEqual(job.trigger_source, LessonIngestionTriggerSource.MANUAL_REINDEX)

        mock_delay.assert_called_once_with(job.id)
        self.assertEqual(response.data['data']['id'], str(job.id))

    @patch('apps.les.tasks.process_lesson_ingestion_job.delay')
    def test_manual_reindex_video_creates_reingest_pending_job(self, mock_delay):
        self.client.force_authenticate(user=self.teacher)

        lesson = self._create_video_lesson(title='Manual Reindex Video')
        response = self.client.post(f'/api/lesson-ingestion/lessons/{lesson.id}/reindex/')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        job = LessonIngestionJob.objects.get(lesson=lesson, trigger_source=LessonIngestionTriggerSource.MANUAL_REINDEX)
        self.assertEqual(job.job_type, LessonIngestionJobType.REINGEST)
        self.assertEqual(job.status, LessonIngestionJobStatus.PENDING)

        mock_delay.assert_called_once_with(job.id)
        self.assertEqual(response.data['data']['id'], str(job.id))

    def test_manual_reindex_rejects_quiz_lesson(self):
        self.client.force_authenticate(user=self.teacher)

        lesson = self._create_quiz_lesson(title='Manual Reindex Quiz')
        response = self.client.post(f'/api/lesson-ingestion/lessons/{lesson.id}/reindex/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['code'], 603)
        self.assertIn('message', response.data)
        self.assertIn('errors', response.data['data'])

    def test_permissions_require_teacher_admin(self):
        # Unauthenticated -> 401
        lesson = self._create_text_lesson(title='Permission Lesson')
        response = self.client.post(f'/api/lesson-ingestion/lessons/{lesson.id}/reindex/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Authenticated learner -> 403
        self.client.force_authenticate(user=self.learner)
        response = self.client.post(f'/api/lesson-ingestion/lessons/{lesson.id}/reindex/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

