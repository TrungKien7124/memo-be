from datetime import timedelta

from rest_framework import status
from rest_framework.test import APITestCase

from unittest.mock import patch

from django.utils import timezone

from apps.app_server.models.course_model import Course, COURSE_STATUS_PUBLISHED
from apps.app_server.models.lesson_model import (
    LESSON_TYPE_QUIZ,
    LESSON_TYPE_TEXT,
    LESSON_TYPE_VIDEO,
    Lesson,
)
from apps.app_server.models.module_model import Module
from apps.app_server.models.user_model import ROLE_STUDENT, ROLE_TEACHER, User
from apps.app_server.models.lesson_progress_model import LessonProgress
from apps.app_server.models.xp_transaction_model import XPTransaction
from apps.app_server.models.user_xp_model import UserXP
from apps.app_server.services.xp_service import XP_AMOUNTS
from apps.app_server.serializers.auth_serializer import get_tokens_for_user
from apps.les.models import (
    LessonIngestionJob,
    LessonIngestionJobStatus,
    LessonIngestionJobType,
    LessonIngestionTriggerSource,
)
from apps.les.tasks import process_lesson_ingestion_job


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
        self.assertEqual(response.data['status'], 'warning')
        self.assertEqual(response.data['code'], 603)
        self.assertIn('message', response.data)
        self.assertIn('old_data', response.data['data'])
        self.assertIn('errors', response.data['data'])

    def test_courses_list_uses_data_meta_envelope(self):
        response = self.client.get('/api/courses/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'success')
        self.assertEqual(response.data['code'], 200)
        self.assertIn('records', response.data['data'])
        self.assertIn('pageinfo', response.data['data'])
        self.assertIsInstance(response.data['data']['records'], list)

    def test_course_detail_uses_data_envelope(self):
        response = self.client.get(f'/api/courses/{self.course.id}/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('data', response.data)
        self.assertEqual(str(response.data['data']['id']), str(self.course.id))

    def test_lesson_detail_uses_data_envelope(self):
        response = self.client.get(f'/api/lessons/{self.video_lesson.id}/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('data', response.data)
        self.assertEqual(response.data['data']['lesson_type'], LESSON_TYPE_VIDEO)

    def test_video_progress_update_uses_data_envelope(self):
        response = self.client.post(
            '/api/lesson-progress/',
            {'lesson': str(self.video_lesson.id), 'watched_seconds': 10},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('data', response.data)
        self.assertNotIn('quiz_result', response.data)
        self.assertTrue(response.data['data']['completed'])

    def test_text_progress_update_uses_data_envelope(self):
        response = self.client.post(
            '/api/lesson-progress/',
            {'lesson': str(self.text_lesson.id), 'completed': True},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('data', response.data)
        self.assertNotIn('quiz_result', response.data)
        self.assertTrue(response.data['data']['completed'])

    def test_quiz_submission_nests_runtime_under_data(self):
        response = self.client.post(
            '/api/lesson-progress/',
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
            '/api/lesson-progress/',
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
            '/api/lesson-progress/',
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
        response = self.client.get('/api/xp/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('data', response.data)
        self.assertIn('total_xp', response.data['data'])

    def test_xp_endpoint_includes_daily_goal_streak_last_seven_days(self):
        daily_goal = XP_AMOUNTS['review']

        today_dt = timezone.now()
        today_date = today_dt.date()
        yesterday_dt = today_dt - timedelta(days=1)

        XPTransaction.objects.create(
            user=self.user,
            xp_amount=daily_goal,
            source='review',
            source_id=None,
            created_at=today_dt,
        )
        XPTransaction.objects.create(
            user=self.user,
            xp_amount=1,
            source='lesson',
            source_id=None,
            created_at=yesterday_dt,
        )

        user_xp, _ = UserXP.objects.get_or_create(user=self.user)
        user_xp.total_xp = daily_goal + 1
        user_xp.weekly_xp = 0
        user_xp.monthly_xp = 0
        user_xp.save(update_fields=['total_xp', 'weekly_xp', 'monthly_xp', 'updated_at'])

        response = self.client.get('/api/xp/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.data['data']

        self.assertEqual(payload['daily_goal'], daily_goal)
        self.assertEqual(payload['streak'], 1)
        self.assertEqual(len(payload['last_seven_days']), 7)
        self.assertTrue(payload['last_seven_days'][-1])
        self.assertFalse(payload['last_seven_days'][-2])

        # weekly_xp/monthly_xp are computed from XPTransaction in the current
        # calendar week and month containing "today".
        week_start = today_date - timedelta(days=today_date.weekday())
        week_end = week_start + timedelta(days=6)

        month_start = today_date.replace(day=1)
        if today_date.month == 12:
            next_month = today_date.replace(year=today_date.year + 1, month=1, day=1)
        else:
            next_month = today_date.replace(month=today_date.month + 1, day=1)
        month_end = next_month - timedelta(days=1)

        expected_weekly = 0
        for d, amount in [(today_date, daily_goal), (yesterday_dt.date(), 1)]:
            if week_start <= d <= week_end:
                expected_weekly += amount

        expected_monthly = 0
        for d, amount in [(today_date, daily_goal), (yesterday_dt.date(), 1)]:
            if month_start <= d <= month_end:
                expected_monthly += amount

        self.assertEqual(payload['weekly_xp'], expected_weekly)
        self.assertEqual(payload['monthly_xp'], expected_monthly)

    def test_lesson_completion_awards_xp_idempotently(self):
        from apps.app_server.models.lesson_model import LESSON_TYPE_VIDEO

        self.assertEqual(self.video_lesson.lesson_type, LESSON_TYPE_VIDEO)

        user_xp, _ = UserXP.objects.get_or_create(user=self.user)
        start_total = user_xp.total_xp

        payload = {'lesson': str(self.video_lesson.id), 'watched_seconds': self.video_lesson.min_watch_time}
        first = self.client.post('/api/lesson-progress/', payload, format='json')
        self.assertIn('data', first.data)
        self.assertTrue(first.data['data']['completed'])

        user_xp.refresh_from_db()
        self.assertEqual(user_xp.total_xp, start_total + XP_AMOUNTS['lesson'])

        second = self.client.post('/api/lesson-progress/', payload, format='json')
        self.assertIn('data', second.data)
        self.assertTrue(second.data['data']['completed'])

        user_xp.refresh_from_db()
        self.assertEqual(user_xp.total_xp, start_total + XP_AMOUNTS['lesson'])

    def test_quiz_completion_awards_xp_idempotently(self):
        user_xp, _ = UserXP.objects.get_or_create(user=self.user)
        start_total = user_xp.total_xp

        payload = {
            'lesson': str(self.quiz_lesson.id),
            'question_index': 0,
            'selected_answer': 0,
        }
        first = self.client.post('/api/lesson-progress/', payload, format='json')
        self.assertIn('data', first.data)
        self.assertTrue(first.data['data']['quiz_runtime']['completed'])

        user_xp.refresh_from_db()
        self.assertEqual(user_xp.total_xp, start_total + XP_AMOUNTS['quiz'])

        second = self.client.post('/api/lesson-progress/', payload, format='json')
        self.assertIn('data', second.data)
        self.assertTrue(second.data['data']['quiz_runtime']['completed'])

        user_xp.refresh_from_db()
        self.assertEqual(user_xp.total_xp, start_total + XP_AMOUNTS['quiz'])

    def test_leaderboard_period_total(self):
        other_user = User.objects.create_user(
            email='leaderboard-other@example.com',
            username='leaderboard-other',
            password=self.password,
            role=ROLE_STUDENT,
        )

        UserXP.objects.create(
            user=self.user,
            total_xp=100,
            weekly_xp=0,
            monthly_xp=0,
        )
        UserXP.objects.create(
            user=other_user,
            total_xp=50,
            weekly_xp=0,
            monthly_xp=0,
        )

        response = self.client.get('/api/leaderboard/?period=total')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('data', response.data)
        self.assertTrue(len(response.data['data']) >= 1)
        self.assertEqual(response.data['data'][0]['xp'], 100)

    def test_leaderboard_period_weekly(self):
        other_user = User.objects.create_user(
            email='leaderboard-weekly-other@example.com',
            username='leaderboard-weekly-other',
            password=self.password,
            role=ROLE_STUDENT,
        )

        today_date = timezone.now().date()
        week_start = today_date - timedelta(days=today_date.weekday())
        week_end = week_start + timedelta(days=6)

        XPTransaction.objects.create(
            user=self.user,
            xp_amount=10,
            source='review',
            source_id=None,
            created_at=timezone.now() if week_start <= today_date <= week_end else timezone.now(),
        )
        XPTransaction.objects.create(
            user=other_user,
            xp_amount=30,
            source='review',
            source_id=None,
            created_at=timezone.now() if week_start <= today_date <= week_end else timezone.now(),
        )

        response = self.client.get('/api/leaderboard/?period=weekly')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('data', response.data)
        self.assertTrue(len(response.data['data']) >= 1)
        self.assertEqual(response.data['data'][0]['xp'], 30)

    def test_leaderboard_period_monthly(self):
        other_user = User.objects.create_user(
            email='leaderboard-monthly-other@example.com',
            username='leaderboard-monthly-other',
            password=self.password,
            role=ROLE_STUDENT,
        )

        today_date = timezone.now().date()
        month_start = today_date.replace(day=1)
        if today_date.month == 12:
            next_month = today_date.replace(year=today_date.year + 1, month=1, day=1)
        else:
            next_month = today_date.replace(month=today_date.month + 1, day=1)
        month_end = next_month - timedelta(days=1)

        XPTransaction.objects.create(
            user=self.user,
            xp_amount=5,
            source='lesson',
            source_id=None,
            created_at=timezone.now() if month_start <= today_date <= month_end else timezone.now(),
        )
        XPTransaction.objects.create(
            user=other_user,
            xp_amount=25,
            source='lesson',
            source_id=None,
            created_at=timezone.now() if month_start <= today_date <= month_end else timezone.now(),
        )

        response = self.client.get('/api/leaderboard/?period=monthly')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('data', response.data)
        self.assertTrue(len(response.data['data']) >= 1)
        self.assertEqual(response.data['data'][0]['xp'], 25)

    def test_leaderboard_invalid_period_rejected(self):
        response = self.client.get('/api/leaderboard/?period=invalid')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['status'], 'warning')
        self.assertEqual(response.data['code'], 604)


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

    @patch('apps.les.tasks.process_lesson_ingestion_job.delay')
    def test_create_text_lesson_enqueues_ingest(self, mock_delay):
        payload = self._build_text_lesson_payload()
        response = self.client.post('/api/lessons/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        job = LessonIngestionJob.objects.get()
        self.assertEqual(job.job_type, LessonIngestionJobType.INGEST)
        self.assertEqual(job.trigger_source, LessonIngestionTriggerSource.LESSON_CREATED)
        self.assertEqual(job.status, LessonIngestionJobStatus.PENDING)
        mock_delay.assert_called_once_with(job.id)

    @patch('apps.les.tasks.process_lesson_ingestion_job.delay')
    def test_create_video_lesson_enqueues_ingest(self, mock_delay):
        payload = self._build_video_lesson_payload()
        response = self.client.post('/api/lessons/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        job = LessonIngestionJob.objects.get()
        self.assertEqual(job.job_type, LessonIngestionJobType.INGEST)
        self.assertEqual(job.trigger_source, LessonIngestionTriggerSource.LESSON_CREATED)
        self.assertEqual(job.status, LessonIngestionJobStatus.PENDING)
        mock_delay.assert_called_once_with(job.id)

    @patch('apps.les.tasks.process_lesson_ingestion_job.delay')
    def test_create_quiz_lesson_does_not_enqueue_job(self, mock_delay):
        payload = self._build_quiz_lesson_payload()
        response = self.client.post('/api/lessons/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertEqual(LessonIngestionJob.objects.count(), 0)
        mock_delay.assert_not_called()

    @patch('apps.les.tasks.process_lesson_ingestion_job.delay')
    def test_update_non_ingestion_fields_does_not_reingest(self, mock_delay):
        create_payload = self._build_text_lesson_payload()
        response = self.client.post('/api/lessons/', create_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        lesson_id = response.data['data']['id']

        LessonIngestionJob.objects.all().delete()
        mock_delay.reset_mock()

        response = self.client.patch(f'/api/lessons/{lesson_id}/', {'order_index': 2}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(LessonIngestionJob.objects.count(), 0)
        mock_delay.assert_not_called()

    @patch('apps.les.tasks.process_lesson_ingestion_job.delay')
    def test_update_ingestion_relevant_fields_enqueues_reingest(self, mock_delay):
        create_payload = self._build_video_lesson_payload()
        response = self.client.post('/api/lessons/', create_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        lesson_id = response.data['data']['id']

        LessonIngestionJob.objects.all().delete()
        mock_delay.reset_mock()

        response = self.client.patch(
            f'/api/lessons/{lesson_id}/',
            {'title': 'New Video Lesson Title'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        job = LessonIngestionJob.objects.get()
        self.assertEqual(job.job_type, LessonIngestionJobType.REINGEST)
        self.assertEqual(job.trigger_source, LessonIngestionTriggerSource.LESSON_UPDATED)
        self.assertEqual(job.status, LessonIngestionJobStatus.PENDING)
        mock_delay.assert_called_once_with(job.id)

    @patch('apps.les.tasks.process_lesson_ingestion_job.delay')
    def test_update_supported_to_quiz_enqueues_delete_index(self, mock_delay):
        create_payload = self._build_text_lesson_payload()
        response = self.client.post('/api/lessons/', create_payload, format='json')
        lesson_id = response.data['data']['id']

        LessonIngestionJob.objects.all().delete()
        mock_delay.reset_mock()

        response = self.client.patch(
            f'/api/lessons/{lesson_id}/',
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

    @patch('apps.les.tasks.process_lesson_ingestion_job.delay')
    def test_update_quiz_to_text_enqueues_ingest(self, mock_delay):
        create_payload = self._build_quiz_lesson_payload()
        response = self.client.post('/api/lessons/', create_payload, format='json')
        lesson_id = response.data['data']['id']

        LessonIngestionJob.objects.all().delete()
        mock_delay.reset_mock()

        response = self.client.patch(
            f'/api/lessons/{lesson_id}/',
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

    @patch('apps.les.tasks.process_lesson_ingestion_job.delay')
    def test_delete_supported_lesson_enqueues_delete_index(self, mock_delay):
        create_payload = self._build_video_lesson_payload()
        response = self.client.post('/api/lessons/', create_payload, format='json')
        lesson_id = response.data['data']['id']

        LessonIngestionJob.objects.all().delete()
        mock_delay.reset_mock()

        response = self.client.delete(f'/api/lessons/{lesson_id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'success')
        self.assertEqual(response.data['code'], 200)
        self.assertIsNone(response.data['data'])

        job = LessonIngestionJob.objects.get()
        self.assertEqual(job.job_type, LessonIngestionJobType.DELETE_INDEX)
        self.assertEqual(job.trigger_source, LessonIngestionTriggerSource.LESSON_DELETED)
        mock_delay.assert_called_once_with(job.id)

    @patch('apps.les.services.lesson_ingestion_processing_service.index_documents')
    def test_celery_task_transitions_job_to_completed(self, mock_index_documents):
        mock_index_documents.side_effect = lambda documents, metadatas=None: [
            f'vec-{i}' for i in range(len(documents))
        ]
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
