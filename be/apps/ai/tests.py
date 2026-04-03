from uuid import uuid4

from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from unittest.mock import MagicMock, patch

from apps.ai.models.acs_conversation_model import Conversation
from apps.ai.models.acs_message_model import Message, ROLE_ASSISTANT, ROLE_USER
from apps.app_server.models.implemented.cms_lesson_model import (
    LESSON_TYPE_QUIZ,
    LESSON_TYPE_TEXT,
    Lesson,
)
from apps.app_server.models.implemented.cms_course_model import Course, COURSE_STATUS_PUBLISHED
from apps.app_server.models.implemented.cms_module_model import Module
from apps.app_server.models.implemented.iam_user_model import ROLE_STUDENT, ROLE_TEACHER, User
from apps.les.models import (
    LessonContentChunk,
    LessonIngestionJob,
    LessonIngestionJobStatus,
    LessonIngestionJobType,
    LessonIngestionTriggerSource,
    LessonSourceDocument,
)


def _create_course_module_lesson(*, teacher, lesson_type, **lesson_overrides):
    course = Course.objects.create(
        title='S3.1 Course',
        description='S3.1 course',
        status=COURSE_STATUS_PUBLISHED,
        created_by=teacher,
    )
    module = Module.objects.create(
        course=course,
        title='Module 1',
        order_index=1,
    )
    lesson = Lesson.objects.create(
        module=module,
        title=lesson_overrides.get('title', 'Lesson'),
        lesson_type=lesson_type,
        content_markdown=lesson_overrides.get('content_markdown', ''),
        video_url=lesson_overrides.get('video_url', ''),
        quiz_questions=lesson_overrides.get('quiz_questions', []),
        is_final=False,
        min_watch_time=10,
        order_index=1,
    )
    return course, module, lesson


def _create_course_module_two_text_lessons(*, teacher):
    course = Course.objects.create(
        title='S3.1 Two Lessons Course',
        description='two lessons',
        status=COURSE_STATUS_PUBLISHED,
        created_by=teacher,
    )
    module = Module.objects.create(
        course=course,
        title='Module 1',
        order_index=1,
    )
    lesson_a = Lesson.objects.create(
        module=module,
        title='Lesson A',
        lesson_type=LESSON_TYPE_TEXT,
        content_markdown='alpha',
        min_watch_time=10,
        order_index=1,
    )
    lesson_b = Lesson.objects.create(
        module=module,
        title='Lesson B',
        lesson_type=LESSON_TYPE_TEXT,
        content_markdown='beta',
        min_watch_time=10,
        order_index=2,
    )
    return course, module, lesson_a, lesson_b


class LessonAwareChatbotS3_1Tests(APITestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            email='teacher-s3-1@example.com',
            username='teacher-s3-1',
            password='Password@123',
            role=ROLE_TEACHER,
        )
        self.client.force_authenticate(user=self.teacher)

    def _create_ingestion_job_and_active_chunks(self, *, lesson, job_status=LessonIngestionJobStatus.COMPLETED):
        ingestion_job = LessonIngestionJob.objects.create(
            lesson=lesson,
            job_type=LessonIngestionJobType.INGEST,
            trigger_source=LessonIngestionTriggerSource.LESSON_CREATED,
            status=job_status,
            source_version='v1',
            started_at=timezone.now(),
            finished_at=timezone.now(),
        )

        source_document = LessonSourceDocument.objects.create(
            lesson=lesson,
            ingestion_job=ingestion_job,
            source_type='text_markdown',
            source_locator='seed',
            raw_text='raw seed',
            normalized_text='normalized seed',
            language_code='en',
            checksum='seed-checksum',
            metadata_json={'seed': True},
        )

        chunk = LessonContentChunk.objects.create(
            lesson=lesson,
            ingestion_job=ingestion_job,
            source_document=source_document,
            chunk_index=0,
            content='normalized seed',
            token_estimate=1,
            char_start=0,
            char_end=len('normalized seed'),
            vector_document_id='vec-seed',
            embedding_provider='chroma',
            embedding_model='nomic-embed-text',
            metadata_json={
                'lesson_id': str(lesson.id),
                'module_id': str(lesson.module.id),
                'course_id': str(lesson.module.course_id),
                'lesson_type': lesson.lesson_type,
                'source_type': 'text_markdown',
                'chunk_index': 0,
                'ingestion_job_id': str(ingestion_job.id),
            },
            is_active=True,
        )

        return ingestion_job, source_document, chunk

    def _create_failed_ingestion_job_without_active_chunks(self, *, lesson):
        failed_job = LessonIngestionJob.objects.create(
            lesson=lesson,
            job_type=LessonIngestionJobType.INGEST,
            trigger_source=LessonIngestionTriggerSource.LESSON_CREATED,
            status=LessonIngestionJobStatus.FAILED,
            source_version='v1',
            started_at=timezone.now(),
            finished_at=timezone.now(),
            error_message='index failed',
            error_payload={'stage': 'index_documents'},
        )
        return failed_job

    @override_settings(AI_RAG_ENABLED=True)
    def test_lesson_aware_request_success_ready_filters_retrieval_by_lesson_id(self):
        _, _, lesson = _create_course_module_lesson(
            teacher=self.teacher,
            lesson_type=LESSON_TYPE_TEXT,
            content_markdown='hello',
        )
        ingestion_job, _, _ = self._create_ingestion_job_and_active_chunks(lesson=lesson)

        retrieve_mock = MagicMock()
        retrieve_docs = ['chunk a', 'chunk b']
        retrieve_mock.return_value = retrieve_docs

        fake_llm = MagicMock()
        fake_llm.chat_completion_with_context.return_value = 'lesson grounded reply'

        with (
            patch('apps.ai.services.acs_chat_service.get_llm_provider', return_value=fake_llm),
            patch('apps.ai.services.providers.get_llm_provider', return_value=fake_llm),
            patch('apps.ai.services.acs_chat_service.retrieve_context', side_effect=retrieve_mock) as mock_retrieve,
        ):
            import apps.ai.services.acs_chat_service as acs_chat_service
            self.assertIs(acs_chat_service.get_llm_provider(), fake_llm)
            from apps.ai.services.acs_chat_service import chat_with_ai
            conv_direct = Conversation.objects.create(user=self.teacher, topic='')
            call_count_before_direct = fake_llm.chat_completion_with_context.call_count
            ai_direct = chat_with_ai(conv_direct, 'direct lesson question', lesson=lesson)
            self.assertEqual(ai_direct.content, 'lesson grounded reply')
            self.assertGreater(fake_llm.chat_completion_with_context.call_count, call_count_before_direct)
            call_count_before_request = fake_llm.chat_completion_with_context.call_count
            response = self.client.post(
                '/api/acs/chat/',
                {
                    'lesson_id': str(lesson.id),
                    'message': 'Explain lesson',
                },
                format='json',
            )
            call_count_after_request = fake_llm.chat_completion_with_context.call_count

        self.assertGreater(call_count_after_request, call_count_before_request)
        if response.status_code != status.HTTP_200_OK:
            raise AssertionError(f'expected {status.HTTP_200_OK} got {response.status_code}, response.data={response.data}')
        self.assertIn('data', response.data)
        payload = response.data['data']
        self.assertEqual(payload['lesson_id'], str(lesson.id))
        self.assertEqual(payload['lesson_context_status'], 'ready')
        self.assertIsNotNone(payload['ai_message'])
        self.assertEqual(payload['ai_message']['role'], ROLE_ASSISTANT)
        self.assertEqual(payload['ai_message']['content'], 'lesson grounded reply')

        # Retrieval must be lesson-scoped.
        mock_retrieve.assert_called()
        _, kwargs = mock_retrieve.call_args
        self.assertEqual(
            kwargs['filters'],
            {'lesson_id': str(lesson.id), 'ingestion_job_id': str(ingestion_job.id)},
        )

        conversation_id = payload['conversation_id']
        conversation = Conversation.objects.get(id=conversation_id, user=self.teacher)
        self.assertEqual(conversation.lesson_id, lesson.id)
        messages = list(conversation.messages.order_by('created_at'))
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0].role, ROLE_USER)
        self.assertEqual(messages[1].role, ROLE_ASSISTANT)

    def test_lesson_aware_request_without_message_fails(self):
        _, _, lesson = _create_course_module_lesson(teacher=self.teacher, lesson_type=LESSON_TYPE_TEXT, content_markdown='hello')
        response = self.client.post(
            '/api/acs/chat/',
            {'lesson_id': str(lesson.id)},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('message', response.data)

    def test_lesson_aware_request_missing_lesson_id_fails_when_lesson_mode_is_requested(self):
        response = self.client.post(
            '/api/acs/chat/',
            {'lesson_id': '', 'message': 'Hi'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('message', response.data)

    @override_settings(AI_RAG_ENABLED=True)
    @patch('apps.ai.services.acs_chat_service.get_llm_provider')
    def test_lesson_supported_but_no_active_chunks_returns_index_pending(self, mock_get_llm_provider):
        _, _, lesson = _create_course_module_lesson(teacher=self.teacher, lesson_type=LESSON_TYPE_TEXT, content_markdown='hello')

        with patch('apps.ai.services.acs_chat_service.retrieve_context') as mock_retrieve:
            response = self.client.post(
                '/api/acs/chat/',
                {'lesson_id': str(lesson.id), 'message': 'Explain'},
                format='json',
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.data['data']
        self.assertEqual(payload['lesson_context_status'], 'index_pending')
        self.assertIsNone(payload['ai_message'])
        mock_get_llm_provider.assert_not_called()
        mock_retrieve.assert_not_called()

    @override_settings(AI_RAG_ENABLED=True)
    def test_lesson_retry_after_index_pending_reuses_conversation_and_then_ready(self):
        _, _, lesson = _create_course_module_lesson(teacher=self.teacher, lesson_type=LESSON_TYPE_TEXT, content_markdown='hello')

        fake_llm = MagicMock()
        fake_llm.chat_completion_with_context.return_value = 'lesson grounded reply'

        with (
            patch('apps.ai.services.acs_chat_service.get_llm_provider', return_value=fake_llm),
            patch('apps.ai.services.providers.get_llm_provider', return_value=fake_llm),
            patch('apps.ai.services.acs_chat_service.retrieve_context', return_value=['ctx']) as mock_retrieve,
        ):
            first_response = self.client.post(
                '/api/acs/chat/',
                {'lesson_id': str(lesson.id), 'message': 'Explain'},
                format='json',
            )

            self.assertEqual(first_response.status_code, status.HTTP_200_OK)
            first_payload = first_response.data['data']
            self.assertEqual(first_payload['lesson_context_status'], 'index_pending')
            self.assertIsNone(first_payload['ai_message'])
            self.assertEqual(fake_llm.chat_completion_with_context.call_count, 0)
            mock_retrieve.assert_not_called()

            conversation_id = first_payload['conversation_id']
            conversation = Conversation.objects.get(id=conversation_id, user=self.teacher)
            self.assertEqual(conversation.lesson_id, lesson.id)
            self.assertEqual(conversation.messages.count(), 0)

            # Once indexing becomes ready, the same conversation should proceed to LLM.
            self._create_ingestion_job_and_active_chunks(lesson=lesson)

            second_response = self.client.post(
                '/api/acs/chat/',
                {
                    'lesson_id': str(lesson.id),
                    'conversation_id': conversation_id,
                    'message': 'Explain again',
                },
                format='json',
            )

            self.assertEqual(second_response.status_code, status.HTTP_200_OK)
            second_payload = second_response.data['data']
            self.assertEqual(second_payload['lesson_context_status'], 'ready')
            self.assertIsNotNone(second_payload['ai_message'])
            self.assertGreater(fake_llm.chat_completion_with_context.call_count, 0)
            mock_retrieve.assert_called()

            conversation.refresh_from_db()
            self.assertEqual(conversation.messages.count(), 2)

    @override_settings(AI_RAG_ENABLED=True)
    @patch('apps.ai.services.acs_chat_service.get_llm_provider')
    def test_lesson_supported_but_latest_job_failed_returns_index_failed(self, mock_get_llm_provider):
        _, _, lesson = _create_course_module_lesson(teacher=self.teacher, lesson_type=LESSON_TYPE_TEXT, content_markdown='hello')
        self._create_failed_ingestion_job_without_active_chunks(lesson=lesson)

        with patch('apps.ai.services.acs_chat_service.retrieve_context') as mock_retrieve:
            response = self.client.post(
                '/api/acs/chat/',
                {'lesson_id': str(lesson.id), 'message': 'Explain'},
                format='json',
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.data['data']
        self.assertEqual(payload['lesson_context_status'], 'index_failed')
        self.assertIsNone(payload['ai_message'])
        mock_get_llm_provider.assert_not_called()
        mock_retrieve.assert_not_called()

    @override_settings(AI_RAG_ENABLED=True)
    @patch('apps.ai.services.acs_chat_service.get_llm_provider')
    def test_lesson_unsupported_quiz_returns_unsupported_lesson(self, mock_get_llm_provider):
        _, _, lesson = _create_course_module_lesson(teacher=self.teacher, lesson_type=LESSON_TYPE_QUIZ)

        with patch('apps.ai.services.acs_chat_service.retrieve_context') as mock_retrieve:
            response = self.client.post(
                '/api/acs/chat/',
                {'lesson_id': str(lesson.id), 'message': 'Explain'},
                format='json',
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.data['data']
        self.assertEqual(payload['lesson_context_status'], 'unsupported_lesson')
        self.assertIsNone(payload['ai_message'])
        mock_get_llm_provider.assert_not_called()
        mock_retrieve.assert_not_called()

    def test_unknown_lesson_id_returns_not_found(self):
        response = self.client.post(
            '/api/acs/chat/',
            {'lesson_id': str(uuid4()), 'message': 'Explain'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('message', response.data)

    @override_settings(AI_RAG_ENABLED=False)
    @patch('apps.ai.services.acs_chat_service.get_llm_provider')
    def test_lesson_ready_but_rag_disabled_returns_index_failed(self, mock_get_llm_provider):
        _, _, lesson = _create_course_module_lesson(teacher=self.teacher, lesson_type=LESSON_TYPE_TEXT, content_markdown='hello')
        self._create_ingestion_job_and_active_chunks(lesson=lesson)

        with patch('apps.ai.services.acs_chat_service.retrieve_context') as mock_retrieve:
            response = self.client.post(
                '/api/acs/chat/',
                {'lesson_id': str(lesson.id), 'message': 'Explain'},
                format='json',
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.data['data']
        self.assertEqual(payload['lesson_context_status'], 'index_failed')
        self.assertIsNone(payload['ai_message'])
        mock_get_llm_provider.assert_not_called()
        mock_retrieve.assert_not_called()

    def test_student_locked_lesson_returns_forbidden(self):
        student = User.objects.create_user(
            email='student-lock@example.com',
            username='student-lock',
            password='Password@123',
            role=ROLE_STUDENT,
        )
        _, _, _lesson_a, lesson_b = _create_course_module_two_text_lessons(teacher=self.teacher)
        self.client.force_authenticate(user=student)
        response = self.client.post(
            '/api/acs/chat/',
            {'lesson_id': str(lesson_b.id), 'message': 'Explain'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('message', response.data)

    @override_settings(AI_RAG_ENABLED=True)
    def test_cross_lesson_conversation_id_reuse_returns_bad_request(self):
        _, _, lesson_a, lesson_b = _create_course_module_two_text_lessons(teacher=self.teacher)
        self._create_ingestion_job_and_active_chunks(lesson=lesson_a)
        self._create_ingestion_job_and_active_chunks(lesson=lesson_b)

        fake_llm = MagicMock()
        fake_llm.chat_completion_with_context.return_value = 'reply a'

        with (
            patch('apps.ai.services.acs_chat_service.get_llm_provider', return_value=fake_llm),
            patch('apps.ai.services.providers.get_llm_provider', return_value=fake_llm),
            patch('apps.ai.services.acs_chat_service.retrieve_context', return_value=['ctx']),
        ):
            first = self.client.post(
                '/api/acs/chat/',
                {'lesson_id': str(lesson_a.id), 'message': 'First'},
                format='json',
            )

        self.assertEqual(first.status_code, status.HTTP_200_OK)
        conversation_id = first.data['data']['conversation_id']
        conversation = Conversation.objects.get(id=conversation_id)
        self.assertEqual(conversation.lesson_id, lesson_a.id)
        message_count_before = conversation.messages.count()
        llm_calls_before = fake_llm.chat_completion_with_context.call_count

        second = self.client.post(
            '/api/acs/chat/',
            {
                'conversation_id': conversation_id,
                'lesson_id': str(lesson_b.id),
                'message': 'Second on wrong lesson',
            },
            format='json',
        )

        self.assertEqual(second.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('message', second.data)
        conversation.refresh_from_db()
        self.assertEqual(conversation.lesson_id, lesson_a.id)
        self.assertEqual(conversation.messages.count(), message_count_before)
        self.assertEqual(fake_llm.chat_completion_with_context.call_count, llm_calls_before)

    @override_settings(AI_RAG_ENABLED=True)
    def test_lesson_mode_rejects_conversation_id_with_prior_generic_messages(self):
        _, _, lesson = _create_course_module_lesson(teacher=self.teacher, lesson_type=LESSON_TYPE_TEXT, content_markdown='hello')
        self._create_ingestion_job_and_active_chunks(lesson=lesson)

        generic_conv = Conversation.objects.create(user=self.teacher, topic='free')
        Message.objects.create(conversation=generic_conv, role=ROLE_USER, content='generic user')
        Message.objects.create(conversation=generic_conv, role=ROLE_ASSISTANT, content='generic assistant')

        fake_llm = MagicMock()
        fake_llm.chat_completion_with_context.return_value = 'should not run'

        with (
            patch('apps.ai.services.acs_chat_service.get_llm_provider', return_value=fake_llm),
            patch('apps.ai.services.providers.get_llm_provider', return_value=fake_llm),
            patch('apps.ai.services.acs_chat_service.retrieve_context') as mock_retrieve,
        ):
            response = self.client.post(
                '/api/acs/chat/',
                {
                    'conversation_id': str(generic_conv.id),
                    'lesson_id': str(lesson.id),
                    'message': 'Lesson question',
                },
                format='json',
            )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('message', response.data)
        generic_conv.refresh_from_db()
        self.assertIsNone(generic_conv.lesson_id)
        self.assertEqual(generic_conv.messages.count(), 2)
        fake_llm.chat_completion_with_context.assert_not_called()
        mock_retrieve.assert_not_called()

