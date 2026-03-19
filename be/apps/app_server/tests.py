from rest_framework import status
from rest_framework.test import APITestCase

from unittest.mock import patch

from apps.app_server.models.implemented.cms_course_model import Course, COURSE_STATUS_PUBLISHED
from apps.app_server.models.implemented.cms_lesson_model import (
    LESSON_TYPE_QUIZ,
    LESSON_TYPE_TEXT,
    LESSON_TYPE_VIDEO,
    Lesson,
)
from apps.app_server.models.implemented.cms_module_model import Module
from apps.app_server.models.implemented.iam_user_model import ROLE_STUDENT, ROLE_TEACHER, User
from apps.app_server.models.implemented.lms_lesson_progress_model import LessonProgress
from apps.app_server.serializers.implemented.iam_auth_serializer import get_tokens_for_user
from apps.lesson_ingestion.models import (
    LessonIngestionJob,
    LessonIngestionJobStatus,
    LessonIngestionJobType,
    LessonIngestionTriggerSource,
)
from apps.lesson_ingestion.tasks import process_lesson_ingestion_job


class CoreContractAPITestCase(APITestCase):
    def setUp(self):
        self.password = 'Password@123'
        self.user = User.objects.create_user(
            email='student@example.com',
            username='student',
            password=self.password,
            role=ROLE_STUDENT,
        )
        self.client.force_authenticate(user=self.user)

        self.course = Course.objects.create(
            title='Core Contract Course',
            description='Contract verification course',
            status=COURSE_STATUS_PUBLISHED,
            created_by=self.user,
        )
        self.module = Module.objects.create(
            course=self.course,
            title='Module 1',
            order_index=1,
        )
        self.video_lesson = Lesson.objects.create(
            module=self.module,
            title='Video Lesson',
            lesson_type=LESSON_TYPE_VIDEO,
            video_url='https://example.com/video.mp4',
            min_watch_time=10,
            order_index=1,
        )
        self.text_lesson = Lesson.objects.create(
            module=self.module,
            title='Text Lesson',
            lesson_type=LESSON_TYPE_TEXT,
            content_markdown='Hello world',
            order_index=2,
        )
        self.quiz_lesson = Lesson.objects.create(
            module=self.module,
            title='Quiz Lesson',
            lesson_type=LESSON_TYPE_QUIZ,
            quiz_questions=[
                {
                    'question': 'Choose A',
                    'options': ['A', 'B', 'C', 'D'],
                    'correct_index': 0,
                }
            ],
            order_index=3,
        )

    def test_register_success_uses_data_envelope(self):
        self.client.force_authenticate(user=None)
        response = self.client.post(
            '/api/auth/register/',
            {
                'email': 'new-user@example.com',
                'username': 'newuser',
                'password': self.password,
                'confirm_password': self.password,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('data', response.data)
        self.assertIn('user', response.data['data'])
        self.assertIn('tokens', response.data['data'])
        self.assertIn('access', response.data['data']['tokens'])
        self.assertIn('refresh', response.data['data']['tokens'])

    def test_login_success_uses_data_envelope(self):
        self.client.force_authenticate(user=None)
        response = self.client.post(
            '/api/auth/login/',
            {'email': self.user.email, 'password': self.password},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('data', response.data)
        self.assertIn('user', response.data['data'])
        self.assertIn('tokens', response.data['data'])

    def test_refresh_success_uses_data_envelope(self):
        self.client.force_authenticate(user=None)
        tokens = get_tokens_for_user(self.user)
        response = self.client.post(
            '/api/auth/refresh/',
            {'refresh': tokens['refresh']},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('data', response.data)
        self.assertIn('access', response.data['data'])

    def test_auth_validation_error_uses_standard_error_envelope(self):
        self.client.force_authenticate(user=None)
        response = self.client.post(
            '/api/auth/register/',
            {'email': 'bad-email'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('message', response.data)
        self.assertIn('old_data', response.data)
        self.assertIn('error', response.data)

    def test_courses_list_uses_data_meta_envelope(self):
        response = self.client.get('/api/cms/courses/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('data', response.data)
        self.assertIn('meta', response.data)
        self.assertIsInstance(response.data['data'], list)

    def test_course_detail_uses_data_envelope(self):
        response = self.client.get(f'/api/cms/courses/{self.course.id}/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('data', response.data)
        self.assertEqual(str(response.data['data']['id']), str(self.course.id))

    def test_lesson_detail_uses_data_envelope(self):
        response = self.client.get(f'/api/cms/lessons/{self.video_lesson.id}/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('data', response.data)
        self.assertEqual(response.data['data']['lesson_type'], LESSON_TYPE_VIDEO)

    def test_video_progress_update_uses_data_envelope(self):
        response = self.client.post(
            '/api/lms/lesson-progress/',
            {'lesson': str(self.video_lesson.id), 'watched_seconds': 10},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('data', response.data)
        self.assertNotIn('quiz_result', response.data)
        self.assertTrue(response.data['data']['completed'])

    def test_text_progress_update_uses_data_envelope(self):
        response = self.client.post(
            '/api/lms/lesson-progress/',
            {'lesson': str(self.text_lesson.id), 'completed': True},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('data', response.data)
        self.assertNotIn('quiz_result', response.data)
        self.assertTrue(response.data['data']['completed'])

    def test_quiz_submission_nests_runtime_under_data(self):
        response = self.client.post(
            '/api/lms/lesson-progress/',
            {
                'lesson': str(self.quiz_lesson.id),
                'question_index': 0,
                'selected_answer': 0,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('data', response.data)
        self.assertNotIn('quiz_result', response.data)
        self.assertIn('quiz_runtime', response.data['data'])
        self.assertTrue(response.data['data']['quiz_runtime']['completed'])
        self.assertEqual(response.data['data']['quiz_runtime']['max_hearts'], 5)

    def test_quiz_wrong_answer_decrements_hearts(self):
        response = self.client.post(
            '/api/lms/lesson-progress/',
            {
                'lesson': str(self.quiz_lesson.id),
                'question_index': 0,
                'selected_answer': 1,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        runtime = response.data['data']['quiz_runtime']
        self.assertFalse(runtime['is_correct'])
        self.assertFalse(runtime['failed'])
        self.assertEqual(runtime['hearts_left'], 4)

    def test_quiz_hearts_reset_behavior_still_works(self):
        LessonProgress.objects.create(
            user=self.user,
            lesson=self.quiz_lesson,
            quiz_hearts_left=1,
            quiz_current_question_index=0,
            quiz_correct_count=0,
        )

        response = self.client.post(
            '/api/lms/lesson-progress/',
            {
                'lesson': str(self.quiz_lesson.id),
                'question_index': 0,
                'selected_answer': 2,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        runtime = response.data['data']['quiz_runtime']
        self.assertTrue(runtime['failed'])
        self.assertEqual(runtime['hearts_left'], 5)
        self.assertEqual(runtime['current_question_index'], 0)
        self.assertEqual(runtime['correct_count'], 0)

    def test_xp_endpoint_uses_data_envelope(self):
        response = self.client.get('/api/gms/xp/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('data', response.data)
        self.assertIn('total_xp', response.data['data'])


class LessonIngestionSchedulingAPITestCase(APITestCase):
    def setUp(self):
        self.password = 'Password@123'
        self.teacher = User.objects.create_user(
            email='teacher@example.com',
            username='teacher',
            password=self.password,
            role=ROLE_TEACHER,
        )
        self.client.force_authenticate(user=self.teacher)

        self.course = Course.objects.create(
            title='Ingestion Scheduling Course',
            description='Course for ingestion scheduling tests',
            status=COURSE_STATUS_PUBLISHED,
            created_by=self.teacher,
        )
        self.module = Module.objects.create(
            course=self.course,
            title='Module 1',
            order_index=1,
        )

    def _build_text_lesson_payload(self, **overrides):
        base = {
            'module': str(self.module.id),
            'title': 'Text Lesson',
            'lesson_type': LESSON_TYPE_TEXT,
            'content_markdown': 'Hello world',
            'order_index': 1,
            'min_watch_time': 10,
            'quiz_questions': [],
            'video_url': '',
            'is_final': False,
        }
        base.update(overrides)
        return base

    def _build_video_lesson_payload(self, **overrides):
        base = {
            'module': str(self.module.id),
            'title': 'Video Lesson',
            'lesson_type': LESSON_TYPE_VIDEO,
            'video_url': 'https://example.com/video.mp4',
            'content_markdown': '',
            'order_index': 1,
            'min_watch_time': 10,
            'quiz_questions': [],
            'is_final': False,
        }
        base.update(overrides)
        return base

    def _build_quiz_lesson_payload(self, **overrides):
        base = {
            'module': str(self.module.id),
            'title': 'Quiz Lesson',
            'lesson_type': LESSON_TYPE_QUIZ,
            'quiz_questions': [
                {
                    'question': 'Choose A',
                    'options': ['A', 'B', 'C', 'D'],
                    'correct_index': 0,
                },
            ],
            'content_markdown': '',
            'video_url': '',
            'order_index': 1,
            'min_watch_time': 10,
            'is_final': False,
        }
        base.update(overrides)
        return base

    @patch('apps.lesson_ingestion.tasks.process_lesson_ingestion_job.delay')
    def test_create_text_lesson_enqueues_ingest(self, mock_delay):
        payload = self._build_text_lesson_payload()
        response = self.client.post('/api/cms/lessons/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        job = LessonIngestionJob.objects.get()
        self.assertEqual(job.job_type, LessonIngestionJobType.INGEST)
        self.assertEqual(job.trigger_source, LessonIngestionTriggerSource.LESSON_CREATED)
        self.assertEqual(job.status, LessonIngestionJobStatus.PENDING)
        mock_delay.assert_called_once_with(job.id)

    @patch('apps.lesson_ingestion.tasks.process_lesson_ingestion_job.delay')
    def test_create_video_lesson_enqueues_ingest(self, mock_delay):
        payload = self._build_video_lesson_payload()
        response = self.client.post('/api/cms/lessons/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        job = LessonIngestionJob.objects.get()
        self.assertEqual(job.job_type, LessonIngestionJobType.INGEST)
        self.assertEqual(job.trigger_source, LessonIngestionTriggerSource.LESSON_CREATED)
        self.assertEqual(job.status, LessonIngestionJobStatus.PENDING)
        mock_delay.assert_called_once_with(job.id)

    @patch('apps.lesson_ingestion.tasks.process_lesson_ingestion_job.delay')
    def test_create_quiz_lesson_does_not_enqueue_job(self, mock_delay):
        payload = self._build_quiz_lesson_payload()
        response = self.client.post('/api/cms/lessons/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertEqual(LessonIngestionJob.objects.count(), 0)
        mock_delay.assert_not_called()

    @patch('apps.lesson_ingestion.tasks.process_lesson_ingestion_job.delay')
    def test_update_non_ingestion_fields_does_not_reingest(self, mock_delay):
        create_payload = self._build_text_lesson_payload()
        response = self.client.post('/api/cms/lessons/', create_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        lesson_id = response.data['data']['id']

        LessonIngestionJob.objects.all().delete()
        mock_delay.reset_mock()

        response = self.client.patch(f'/api/cms/lessons/{lesson_id}/', {'order_index': 2}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(LessonIngestionJob.objects.count(), 0)
        mock_delay.assert_not_called()

    @patch('apps.lesson_ingestion.tasks.process_lesson_ingestion_job.delay')
    def test_update_ingestion_relevant_fields_enqueues_reingest(self, mock_delay):
        create_payload = self._build_video_lesson_payload()
        response = self.client.post('/api/cms/lessons/', create_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        lesson_id = response.data['data']['id']

        LessonIngestionJob.objects.all().delete()
        mock_delay.reset_mock()

        response = self.client.patch(
            f'/api/cms/lessons/{lesson_id}/',
            {'title': 'New Video Lesson Title'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        job = LessonIngestionJob.objects.get()
        self.assertEqual(job.job_type, LessonIngestionJobType.REINGEST)
        self.assertEqual(job.trigger_source, LessonIngestionTriggerSource.LESSON_UPDATED)
        self.assertEqual(job.status, LessonIngestionJobStatus.PENDING)
        mock_delay.assert_called_once_with(job.id)

    @patch('apps.lesson_ingestion.tasks.process_lesson_ingestion_job.delay')
    def test_update_supported_to_quiz_enqueues_delete_index(self, mock_delay):
        create_payload = self._build_text_lesson_payload()
        response = self.client.post('/api/cms/lessons/', create_payload, format='json')
        lesson_id = response.data['data']['id']

        LessonIngestionJob.objects.all().delete()
        mock_delay.reset_mock()

        response = self.client.patch(
            f'/api/cms/lessons/{lesson_id}/',
            {
                'lesson_type': LESSON_TYPE_QUIZ,
                'quiz_questions': [
                    {
                        'question': 'Choose A',
                        'options': ['A', 'B', 'C', 'D'],
                        'correct_index': 0,
                    },
                ],
                'is_final': False,
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        job = LessonIngestionJob.objects.get()
        self.assertEqual(job.job_type, LessonIngestionJobType.DELETE_INDEX)
        self.assertEqual(job.trigger_source, LessonIngestionTriggerSource.LESSON_UPDATED)
        mock_delay.assert_called_once_with(job.id)

    @patch('apps.lesson_ingestion.tasks.process_lesson_ingestion_job.delay')
    def test_update_quiz_to_text_enqueues_ingest(self, mock_delay):
        create_payload = self._build_quiz_lesson_payload()
        response = self.client.post('/api/cms/lessons/', create_payload, format='json')
        lesson_id = response.data['data']['id']

        LessonIngestionJob.objects.all().delete()
        mock_delay.reset_mock()

        response = self.client.patch(
            f'/api/cms/lessons/{lesson_id}/',
            {
                'lesson_type': LESSON_TYPE_TEXT,
                'content_markdown': 'Hello reingested text',
                'is_final': False,
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        job = LessonIngestionJob.objects.get()
        self.assertEqual(job.job_type, LessonIngestionJobType.INGEST)
        self.assertEqual(job.trigger_source, LessonIngestionTriggerSource.LESSON_UPDATED)
        mock_delay.assert_called_once_with(job.id)

    @patch('apps.lesson_ingestion.tasks.process_lesson_ingestion_job.delay')
    def test_delete_supported_lesson_enqueues_delete_index(self, mock_delay):
        create_payload = self._build_video_lesson_payload()
        response = self.client.post('/api/cms/lessons/', create_payload, format='json')
        lesson_id = response.data['data']['id']

        LessonIngestionJob.objects.all().delete()
        mock_delay.reset_mock()

        response = self.client.delete(f'/api/cms/lessons/{lesson_id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        job = LessonIngestionJob.objects.get()
        self.assertEqual(job.job_type, LessonIngestionJobType.DELETE_INDEX)
        self.assertEqual(job.trigger_source, LessonIngestionTriggerSource.LESSON_DELETED)
        mock_delay.assert_called_once_with(job.id)

    def test_celery_task_transitions_job_to_completed(self):
        lesson = Lesson.objects.create(
            module=self.module,
            title='Task Lesson',
            lesson_type=LESSON_TYPE_TEXT,
            content_markdown='hello',
            min_watch_time=10,
            order_index=1,
        )
        job = LessonIngestionJob.objects.create(
            lesson=lesson,
            job_type=LessonIngestionJobType.INGEST,
            trigger_source=LessonIngestionTriggerSource.LESSON_CREATED,
            source_version='v1',
            status=LessonIngestionJobStatus.PENDING,
        )

        process_lesson_ingestion_job.run(str(job.id))
        job.refresh_from_db()
        self.assertEqual(job.status, LessonIngestionJobStatus.COMPLETED)
        self.assertIsNotNone(job.started_at)
        self.assertIsNotNone(job.finished_at)
