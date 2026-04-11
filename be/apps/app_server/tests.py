from datetime import timedelta
from urllib.parse import urlparse
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings

from rest_framework import status
from rest_framework.test import APITestCase

from unittest.mock import patch

from django.utils import timezone

from apps.app_server.models.course_model import Course, COURSE_STATUS_PUBLISHED
from apps.app_server.models.course_enrollment_model import CourseEnrollment
from apps.app_server.models.lesson_model import (
    LESSON_TYPE_LESSON,
    LESSON_TYPE_QUIZ,
    LESSON_TYPE_TEXT,
    LESSON_TYPE_VIDEO,
    PUBLICATION_STATUS_FAILED,
    PUBLICATION_STATUS_PROCESSING,
    TRANSCRIPT_STATUS_FAILED,
    TRANSCRIPT_STATUS_NOT_STARTED,
    TRANSCRIPT_STATUS_READY,
    Lesson,
)
from apps.app_server.models.lesson_comment_model import LessonComment
from apps.app_server.models.module_model import Module
from apps.app_server.models.user_model import ROLE_ADMIN, ROLE_STUDENT, ROLE_TEACHER, User
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
from apps.les.tasks import process_lesson_ingestion_job, process_lesson_video_transcription


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
        CourseEnrollment.objects.create(user=self.user, course=self.course)

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

    def test_login_success_with_username_uses_data_envelope(self):
        self.client.force_authenticate(user=None)
        response = self.client.post(
            '/api/auth/login/',
            {'email': self.user.username, 'password': self.password},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('data', response.data)
        self.assertIn('user', response.data['data'])
        self.assertIn('tokens', response.data['data'])
        self.assertEqual(response.data['data']['user']['username'], self.user.username)

    def test_login_blank_identifier_fails_with_validation_shape(self):
        self.client.force_authenticate(user=None)
        response = self.client.post(
            '/api/auth/login/',
            {'email': '   ', 'password': self.password},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['status'], 'warning')
        self.assertEqual(response.data['code'], 603)
        self.assertIn('data', response.data)
        self.assertIn('errors', response.data['data'])
        self.assertIn('email', response.data['data']['errors'])

    def test_login_invalid_identifier_fails_with_standard_error_envelope(self):
        self.client.force_authenticate(user=None)
        response = self.client.post(
            '/api/auth/login/',
            {'email': 'unknown-user', 'password': self.password},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['status'], 'warning')
        self.assertEqual(response.data['code'], 603)
        self.assertIn('message', response.data)

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

    def test_courses_payload_includes_is_enrolled(self):
        response = self.client.get('/api/courses/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        records = response.data['data']['records']
        self.assertIn('is_enrolled', records[0])

    def test_course_detail_payload_includes_is_enrolled(self):
        response = self.client.get(f'/api/courses/{self.course.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('is_enrolled', response.data['data'])
        self.assertTrue(response.data['data']['is_enrolled'])

    def test_enroll_endpoint_creates_enrollment(self):
        self.client.force_authenticate(user=None)
        other_user = User.objects.create_user(
            email='enroll-student@example.com',
            username='enroll-student',
            password=self.password,
            role=ROLE_STUDENT,
        )
        self.client.force_authenticate(user=other_user)
        self.assertFalse(CourseEnrollment.objects.filter(user=other_user, course=self.course).exists())

        response = self.client.post(f'/api/courses/{self.course.id}/enroll/', {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(CourseEnrollment.objects.filter(user=other_user, course=self.course).exists())
        self.assertTrue(response.data['data']['is_enrolled'])

    def test_enroll_endpoint_is_idempotent(self):
        response_1 = self.client.post(f'/api/courses/{self.course.id}/enroll/', {}, format='json')
        response_2 = self.client.post(f'/api/courses/{self.course.id}/enroll/', {}, format='json')
        self.assertEqual(response_1.status_code, status.HTTP_200_OK)
        self.assertEqual(response_2.status_code, status.HTTP_200_OK)
        self.assertEqual(CourseEnrollment.objects.filter(user=self.user, course=self.course).count(), 1)

    def test_non_enrolled_user_cannot_access_modules(self):
        self.client.force_authenticate(user=None)
        other_user = User.objects.create_user(
            email='no-module-access@example.com',
            username='no-module-access',
            password=self.password,
            role=ROLE_STUDENT,
        )
        self.client.force_authenticate(user=other_user)

        response = self.client.get(f'/api/modules/?course={self.course.id}')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data['status'], 'error')
        self.assertEqual(response.data['code'], 602)

    def test_non_enrolled_user_cannot_access_lessons(self):
        self.client.force_authenticate(user=None)
        other_user = User.objects.create_user(
            email='no-lesson-access@example.com',
            username='no-lesson-access',
            password=self.password,
            role=ROLE_STUDENT,
        )
        self.client.force_authenticate(user=other_user)

        response = self.client.get(f'/api/lessons/?module={self.module.id}')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data['status'], 'error')
        self.assertEqual(response.data['code'], 602)

    def test_non_enrolled_user_cannot_submit_lesson_progress(self):
        self.client.force_authenticate(user=None)
        other_user = User.objects.create_user(
            email='no-progress-access@example.com',
            username='no-progress-access',
            password=self.password,
            role=ROLE_STUDENT,
        )
        self.client.force_authenticate(user=other_user)

        response = self.client.post(
            '/api/lesson-progress/',
            {'lesson': str(self.video_lesson.id), 'watched_seconds': 10},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data['status'], 'error')
        self.assertEqual(response.data['code'], 602)

    def test_enrolled_user_can_access_modules_lessons_and_progress(self):
        response_modules = self.client.get(f'/api/modules/?course={self.course.id}')
        response_lessons = self.client.get(f'/api/lessons/?module={self.module.id}')
        response_progress = self.client.post(
            '/api/lesson-progress/',
            {'lesson': str(self.video_lesson.id), 'watched_seconds': 10},
            format='json',
        )

        self.assertEqual(response_modules.status_code, status.HTTP_200_OK)
        self.assertEqual(response_lessons.status_code, status.HTTP_200_OK)
        self.assertIn(response_progress.status_code, (status.HTTP_200_OK, status.HTTP_201_CREATED))

    def test_admin_bypass_course_access_still_works(self):
        self.client.force_authenticate(user=None)
        admin_user = User.objects.create_user(
            email='admin-access@example.com',
            username='admin-access',
            password=self.password,
            role=ROLE_ADMIN,
        )
        self.client.force_authenticate(user=admin_user)

        response_modules = self.client.get(f'/api/modules/?course={self.course.id}')
        response_lessons = self.client.get(f'/api/lessons/?module={self.module.id}')
        response_progress = self.client.post(
            '/api/lesson-progress/',
            {'lesson': str(self.video_lesson.id), 'watched_seconds': 10},
            format='json',
        )
        self.assertEqual(response_modules.status_code, status.HTTP_200_OK)
        self.assertEqual(response_lessons.status_code, status.HTTP_200_OK)
        self.assertIn(response_progress.status_code, (status.HTTP_200_OK, status.HTTP_201_CREATED))

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

    def test_lesson_progress_requires_watch_time_to_complete(self):
        response = self.client.post(
            '/api/lesson-progress/',
            {'lesson': str(self.text_lesson.id), 'completed': True},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('data', response.data)
        self.assertNotIn('quiz_result', response.data)
        self.assertFalse(response.data['data']['completed'])

        second_response = self.client.post(
            '/api/lesson-progress/',
            {'lesson': str(self.text_lesson.id), 'watched_seconds': self.text_lesson.min_watch_time},
            format='json',
        )
        self.assertEqual(second_response.status_code, status.HTTP_200_OK)
        self.assertTrue(second_response.data['data']['completed'])

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


class CourseAccessManagementAPITestCase(APITestCase):
    def setUp(self):
        self.password = 'Password@123'
        self.admin = User.objects.create_user(
            email='admin-course-access@example.com',
            username='admin-course-access',
            password=self.password,
            role=ROLE_ADMIN,
        )
        self.teacher_1 = User.objects.create_user(
            email='teacher-1@example.com',
            username='teacher-1',
            password=self.password,
            role=ROLE_TEACHER,
        )
        self.teacher_2 = User.objects.create_user(
            email='teacher-2@example.com',
            username='teacher-2',
            password=self.password,
            role=ROLE_TEACHER,
        )
        self.student = User.objects.create_user(
            email='student-course-access@example.com',
            username='student-course-access',
            password=self.password,
            role=ROLE_STUDENT,
        )

        self.course = Course.objects.create(
            title='Managed Access Course',
            description='Course for access management tests',
            status=COURSE_STATUS_PUBLISHED,
            created_by=self.admin,
        )
        self.module_1 = Module.objects.create(
            course=self.course,
            title='Module 1',
            order_index=1,
        )
        self.module_2 = Module.objects.create(
            course=self.course,
            title='Module 2',
            order_index=2,
        )
        self.lesson_1 = Lesson.objects.create(
            module=self.module_1,
            title='Lesson 1',
            lesson_type=LESSON_TYPE_TEXT,
            content_markdown='Lesson 1 content',
            order_index=1,
        )
        self.lesson_2 = Lesson.objects.create(
            module=self.module_1,
            title='Lesson 2',
            lesson_type=LESSON_TYPE_TEXT,
            content_markdown='Lesson 2 content',
            order_index=2,
        )
        self.lesson_3 = Lesson.objects.create(
            module=self.module_2,
            title='Lesson 3',
            lesson_type=LESSON_TYPE_TEXT,
            content_markdown='Lesson 3 content',
            order_index=1,
        )

    def _admin_client(self):
        self.client.force_authenticate(user=self.admin)

    def _teacher_client(self):
        self.client.force_authenticate(user=self.teacher_1)

    def _student_client(self):
        self.client.force_authenticate(user=self.student)

    def test_admin_can_grant_access_to_student(self):
        self._admin_client()
        response = self.client.post(
            f'/api/courses/{self.course.id}/enrollments/',
            {'user_id': str(self.student.id)},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(CourseEnrollment.objects.filter(user=self.student, course=self.course).exists())
        self.assertEqual(response.data['data']['source'], CourseEnrollment.SOURCE_ADMIN_GRANT)

    def test_admin_can_grant_access_to_teacher(self):
        self._admin_client()
        response = self.client.post(
            f'/api/courses/{self.course.id}/enrollments/',
            {'user_id': str(self.teacher_1.id)},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(CourseEnrollment.objects.filter(user=self.teacher_1, course=self.course).exists())
        self.assertEqual(response.data['data']['source'], CourseEnrollment.SOURCE_ADMIN_GRANT)

    def test_admin_can_revoke_access(self):
        enrollment = CourseEnrollment.objects.create(
            user=self.teacher_1,
            course=self.course,
            source=CourseEnrollment.SOURCE_ADMIN_GRANT,
            granted_by=self.admin,
        )
        self._admin_client()
        response = self.client.delete(f'/api/courses/{self.course.id}/enrollments/{enrollment.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(CourseEnrollment.objects.filter(id=enrollment.id).exists())

    def test_admin_can_bulk_grant_all_teachers(self):
        self._admin_client()
        response = self.client.post(
            f'/api/courses/{self.course.id}/enrollments/bulk-grant-teachers/',
            {},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['created_count'], 2)
        self.assertEqual(CourseEnrollment.objects.filter(course=self.course, user__role=ROLE_TEACHER).count(), 2)

    def test_bulk_grant_teachers_is_idempotent(self):
        self._admin_client()
        first = self.client.post(f'/api/courses/{self.course.id}/enrollments/bulk-grant-teachers/', {}, format='json')
        second = self.client.post(f'/api/courses/{self.course.id}/enrollments/bulk-grant-teachers/', {}, format='json')
        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(second.data['data']['created_count'], 0)
        self.assertEqual(second.data['data']['existing_count'], 2)

    def test_non_admin_cannot_manage_course_access_apis(self):
        self._student_client()
        list_response = self.client.get(f'/api/courses/{self.course.id}/enrollments/')
        grant_response = self.client.post(
            f'/api/courses/{self.course.id}/enrollments/',
            {'user_id': str(self.teacher_1.id)},
            format='json',
        )
        bulk_response = self.client.post(f'/api/courses/{self.course.id}/enrollments/bulk-grant-teachers/', {}, format='json')

        self.assertEqual(list_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(grant_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(bulk_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(list_response.data['code'], 602)
        self.assertEqual(grant_response.data['code'], 602)
        self.assertEqual(bulk_response.data['code'], 602)

    def test_teacher_without_enrollment_cannot_access_course_content(self):
        self._teacher_client()
        modules_response = self.client.get(f'/api/modules/?course={self.course.id}')
        lessons_response = self.client.get(f'/api/lessons/?module={self.module_1.id}')
        progress_response = self.client.post(
            '/api/lesson-progress/',
            {'lesson': str(self.lesson_1.id), 'completed': True},
            format='json',
        )

        self.assertEqual(modules_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(lessons_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(progress_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(modules_response.data['code'], 602)
        self.assertEqual(lessons_response.data['code'], 602)
        self.assertEqual(progress_response.data['code'], 602)

    def test_teacher_with_enrollment_can_access_course_content(self):
        CourseEnrollment.objects.create(
            user=self.teacher_1,
            course=self.course,
            source=CourseEnrollment.SOURCE_ADMIN_GRANT,
            granted_by=self.admin,
        )
        self._teacher_client()
        modules_response = self.client.get(f'/api/modules/?course={self.course.id}')
        lessons_response = self.client.get(f'/api/lessons/?module={self.module_1.id}')
        progress_response = self.client.post(
            '/api/lesson-progress/',
            {'lesson': str(self.lesson_1.id), 'completed': True},
            format='json',
        )

        self.assertEqual(modules_response.status_code, status.HTTP_200_OK)
        self.assertEqual(lessons_response.status_code, status.HTTP_200_OK)
        self.assertIn(progress_response.status_code, (status.HTTP_200_OK, status.HTTP_201_CREATED))

    def test_teacher_with_enrollment_sees_all_modules_unlocked(self):
        CourseEnrollment.objects.create(
            user=self.teacher_1,
            course=self.course,
            source=CourseEnrollment.SOURCE_ADMIN_GRANT,
            granted_by=self.admin,
        )
        self._teacher_client()
        response = self.client.get(f'/api/modules/?course={self.course.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        records = response.data['data']['records']
        self.assertTrue(all(module['is_unlocked'] for module in records))

    def test_teacher_with_enrollment_sees_lessons_not_locked(self):
        CourseEnrollment.objects.create(
            user=self.teacher_1,
            course=self.course,
            source=CourseEnrollment.SOURCE_ADMIN_GRANT,
            granted_by=self.admin,
        )
        self._teacher_client()
        response = self.client.get(f'/api/lessons/?module={self.module_1.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        records = response.data['data']['records']
        self.assertTrue(all(lesson['status'] in ('current', 'completed') for lesson in records))

    def test_student_with_enrollment_keeps_sequential_unlock_behavior(self):
        CourseEnrollment.objects.create(
            user=self.student,
            course=self.course,
            source=CourseEnrollment.SOURCE_ADMIN_GRANT,
            granted_by=self.admin,
        )
        self._student_client()
        modules_response = self.client.get(f'/api/modules/?course={self.course.id}')
        self.assertEqual(modules_response.status_code, status.HTTP_200_OK)
        modules = modules_response.data['data']['records']
        self.assertTrue(modules[0]['is_unlocked'])
        self.assertFalse(modules[1]['is_unlocked'])

        lessons_response = self.client.get(f'/api/lessons/?module={self.module_1.id}')
        self.assertEqual(lessons_response.status_code, status.HTTP_200_OK)
        lessons = lessons_response.data['data']['records']
        self.assertEqual(lessons[0]['status'], 'current')
        self.assertEqual(lessons[1]['status'], 'locked')

    def test_admin_bypass_still_works_without_enrollment(self):
        self._admin_client()
        modules_response = self.client.get(f'/api/modules/?course={self.course.id}')
        lessons_response = self.client.get(f'/api/lessons/?module={self.module_1.id}')
        progress_response = self.client.post(
            '/api/lesson-progress/',
            {'lesson': str(self.lesson_1.id), 'completed': True},
            format='json',
        )
        self.assertEqual(modules_response.status_code, status.HTTP_200_OK)
        self.assertEqual(lessons_response.status_code, status.HTTP_200_OK)
        self.assertIn(progress_response.status_code, (status.HTTP_200_OK, status.HTTP_201_CREATED))


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
            'title': 'Lesson',
            'lesson_type': LESSON_TYPE_LESSON,
            'content_markdown': 'Hello world summary',
            'video_url': 'https://example.com/lesson.mp4',
            'order_index': 1,
            'min_watch_time': 10,
            'quiz_questions': [],
            'is_final': False,
        }
        base.update(overrides)
        return base

    def _build_video_lesson_payload(self, **overrides):
        base = {
            'module': str(self.module.id),
            'title': 'Lesson',
            'lesson_type': LESSON_TYPE_LESSON,
            'video_url': 'https://example.com/video.mp4',
            'content_markdown': 'Lesson summary',
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

    @patch('apps.les.services.lesson_ingestion_processing_service.index_documents')
    @patch('apps.les.tasks.process_lesson_ingestion_job.delay')
    def test_update_transcript_text_for_video_lesson_enqueues_reingest_and_builds_source_document(
        self,
        mock_delay,
        mock_index_documents,
    ):
        mock_index_documents.side_effect = lambda documents, metadatas=None: [
            f'vec-{i}' for i in range(len(documents))
        ]
        lesson = Lesson.objects.create(
            module=self.module,
            title='Video with Manual Transcript',
            lesson_type=LESSON_TYPE_LESSON,
            content_markdown='Summary block',
            video_url='',
            video_file=SimpleUploadedFile('video.mp4', b'\x00' * 512, content_type='video/mp4'),
            transcript_text='old transcript',
            transcript_status=TRANSCRIPT_STATUS_READY,
            min_watch_time=10,
            order_index=1,
        )
        initial_job = LessonIngestionJob.objects.create(
            lesson=lesson,
            job_type=LessonIngestionJobType.INGEST,
            trigger_source=LessonIngestionTriggerSource.LESSON_CREATED,
            status=LessonIngestionJobStatus.COMPLETED,
            source_version='v1',
        )
        _ = initial_job.id
        mock_delay.reset_mock()

        response = self.client.patch(
            f'/api/lessons/{lesson.id}/',
            {'transcript_text': 'new transcript from admin'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        pending_job = LessonIngestionJob.objects.filter(lesson=lesson).order_by('-created_at').first()
        self.assertIsNotNone(pending_job)
        self.assertEqual(pending_job.status, LessonIngestionJobStatus.PENDING)
        self.assertEqual(pending_job.job_type, LessonIngestionJobType.REINGEST)
        mock_delay.assert_called_once_with(pending_job.id)

        process_lesson_ingestion_job.run(str(pending_job.id))
        pending_job.refresh_from_db()
        self.assertEqual(pending_job.status, LessonIngestionJobStatus.COMPLETED)
        source_document = pending_job.source_documents.order_by('-created_at').first()
        self.assertIsNotNone(source_document)
        self.assertIn('Summary block', source_document.raw_text)
        self.assertIn('new transcript from admin', source_document.raw_text)

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
                'content_markdown': 'Hello reingested lesson summary',
                'video_url': 'https://example.com/reingest.mp4',
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
            lesson_type=LESSON_TYPE_LESSON,
            content_markdown='hello',
            video_url='https://example.com/task.mp4',
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


class LessonCommentAPITestCase(APITestCase):
    def setUp(self):
        self.password = 'Password@123'
        self.admin = User.objects.create_user(
            email='admin-comment@example.com',
            username='admin-comment',
            password=self.password,
            role=ROLE_ADMIN,
        )
        self.teacher = User.objects.create_user(
            email='teacher-comment@example.com',
            username='teacher-comment',
            password=self.password,
            role=ROLE_TEACHER,
        )
        self.student = User.objects.create_user(
            email='student-comment@example.com',
            username='student-comment',
            password=self.password,
            role=ROLE_STUDENT,
        )
        self.other_student = User.objects.create_user(
            email='other-student-comment@example.com',
            username='other-student-comment',
            password=self.password,
            role=ROLE_STUDENT,
        )

        self.course = Course.objects.create(
            title='Comment Course',
            description='Course for lesson comments',
            status=COURSE_STATUS_PUBLISHED,
            created_by=self.admin,
        )
        self.module = Module.objects.create(course=self.course, title='Module', order_index=1)
        self.lesson = Lesson.objects.create(
            module=self.module,
            title='Lesson',
            lesson_type=LESSON_TYPE_LESSON,
            video_url='https://example.com/lesson.mp4',
            content_markdown='Lesson summary',
            min_watch_time=10,
            order_index=1,
        )
        self.other_lesson = Lesson.objects.create(
            module=self.module,
            title='Other Lesson',
            lesson_type=LESSON_TYPE_LESSON,
            video_url='https://example.com/other.mp4',
            content_markdown='Other summary',
            min_watch_time=10,
            order_index=2,
        )

        CourseEnrollment.objects.create(user=self.teacher, course=self.course)
        CourseEnrollment.objects.create(user=self.student, course=self.course)

    def test_enrolled_student_can_list_comments(self):
        LessonComment.objects.create(lesson=self.lesson, user=self.teacher, content='Hello class')
        self.client.force_authenticate(user=self.student)
        response = self.client.get(f'/api/lesson-comments/?lesson={self.lesson.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'success')
        self.assertEqual(len(response.data['data']), 1)

    def test_non_enrolled_user_forbidden_to_list_comments(self):
        self.client.force_authenticate(user=self.other_student)
        response = self.client.get(f'/api/lesson-comments/?lesson={self.lesson.id}')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data['code'], 602)

    def test_non_enrolled_user_forbidden_to_retrieve_comment(self):
        comment = LessonComment.objects.create(lesson=self.lesson, user=self.teacher, content='Secret thread')
        self.client.force_authenticate(user=self.other_student)
        response = self.client.get(f'/api/lesson-comments/{comment.id}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data['code'], 602)

    def test_enrolled_teacher_can_create_top_level_comment(self):
        self.client.force_authenticate(user=self.teacher)
        response = self.client.post(
            '/api/lesson-comments/',
            {'lesson': str(self.lesson.id), 'content': 'Teacher comment'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['data']['user_role'], ROLE_TEACHER)

    def test_enrolled_student_can_reply_to_teacher_comment(self):
        parent = LessonComment.objects.create(lesson=self.lesson, user=self.teacher, content='Question?')
        self.client.force_authenticate(user=self.student)
        response = self.client.post(
            '/api/lesson-comments/',
            {'lesson': str(self.lesson.id), 'parent': str(parent.id), 'content': 'Answer'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['data']['parent'], str(parent.id))

    def test_parent_comment_from_another_lesson_is_rejected(self):
        parent = LessonComment.objects.create(lesson=self.other_lesson, user=self.teacher, content='Other thread')
        self.client.force_authenticate(user=self.student)
        response = self.client.post(
            '/api/lesson-comments/',
            {'lesson': str(self.lesson.id), 'parent': str(parent.id), 'content': 'Invalid reply'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['code'], 603)

    def test_owner_can_edit_own_comment(self):
        comment = LessonComment.objects.create(lesson=self.lesson, user=self.student, content='Original')
        self.client.force_authenticate(user=self.student)
        response = self.client.patch(
            f'/api/lesson-comments/{comment.id}/',
            {'content': 'Updated'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['content'], 'Updated')

    def test_non_owner_cannot_edit_other_comment(self):
        comment = LessonComment.objects.create(lesson=self.lesson, user=self.teacher, content='Teacher note')
        self.client.force_authenticate(user=self.student)
        response = self.client.patch(
            f'/api/lesson-comments/{comment.id}/',
            {'content': 'Hijack'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data['code'], 602)

    def test_owner_can_soft_delete_own_comment(self):
        comment = LessonComment.objects.create(lesson=self.lesson, user=self.student, content='Delete me')
        self.client.force_authenticate(user=self.student)
        response = self.client.delete(f'/api/lesson-comments/{comment.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        comment.refresh_from_db()
        self.assertTrue(comment.is_deleted)
        self.assertEqual(comment.content, '')

    def test_admin_can_soft_delete_other_user_comment(self):
        comment = LessonComment.objects.create(lesson=self.lesson, user=self.student, content='Delete by admin')
        self.client.force_authenticate(user=self.admin)
        response = self.client.delete(f'/api/lesson-comments/{comment.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        comment.refresh_from_db()
        self.assertTrue(comment.is_deleted)

    def test_deleted_parent_keeps_thread_shape_with_replies(self):
        parent = LessonComment.objects.create(lesson=self.lesson, user=self.teacher, content='Parent')
        child = LessonComment.objects.create(
            lesson=self.lesson,
            user=self.student,
            parent=parent,
            content='Child reply',
        )
        self.client.force_authenticate(user=self.teacher)
        self.client.delete(f'/api/lesson-comments/{parent.id}/')
        response = self.client.get(f'/api/lesson-comments/?lesson={self.lesson.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.data['data']
        parent_row = next(item for item in payload if item['id'] == str(parent.id))
        child_row = next(item for item in payload if item['id'] == str(child.id))
        self.assertTrue(parent_row['is_deleted'])
        self.assertEqual(parent_row['content'], '[deleted]')
        self.assertEqual(child_row['parent'], str(parent.id))

    def test_comment_list_includes_user_metadata(self):
        LessonComment.objects.create(lesson=self.lesson, user=self.teacher, content='Meta')
        self.client.force_authenticate(user=self.student)
        response = self.client.get(f'/api/lesson-comments/?lesson={self.lesson.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        item = response.data['data'][0]
        self.assertIn('user_id', item)
        self.assertIn('user_email', item)
        self.assertIn('user_username', item)
        self.assertIn('user_role', item)

    def test_model_layer_rejects_cross_lesson_parent(self):
        parent = LessonComment.objects.create(lesson=self.other_lesson, user=self.teacher, content='Other parent')
        invalid_comment = LessonComment(
            lesson=self.lesson,
            user=self.student,
            parent=parent,
            content='Cross lesson invalid',
        )
        with self.assertRaises(ValidationError):
            invalid_comment.save()


class CourseAndModuleExtendStoreAPITestCase(APITestCase):
    def setUp(self):
        self.password = 'Password@123'
        self.teacher = User.objects.create_user(
            email='teacher-extend@example.com',
            username='teacher-extend',
            password=self.password,
            role=ROLE_TEACHER,
        )
        self.student = User.objects.create_user(
            email='student-extend@example.com',
            username='student-extend',
            password=self.password,
            role=ROLE_STUDENT,
        )
        self.client.force_authenticate(user=self.teacher)

        self.course = Course.objects.create(
            title='Extend Course',
            description='Base',
            status=COURSE_STATUS_PUBLISHED,
            created_by=self.teacher,
        )
        self.module_a = Module.objects.create(course=self.course, title='A', order_index=1)
        self.module_b = Module.objects.create(course=self.course, title='B', order_index=2)
        self.module_c = Module.objects.create(course=self.course, title='C', order_index=3)

        self.lesson_a1 = Lesson.objects.create(
            module=self.module_a,
            title='L1',
            lesson_type=LESSON_TYPE_LESSON,
            content_markdown='x',
            video_url='https://example.com/1',
            min_watch_time=5,
            order_index=1,
        )
        self.lesson_a2 = Lesson.objects.create(
            module=self.module_a,
            title='L2',
            lesson_type=LESSON_TYPE_LESSON,
            content_markdown='y',
            video_url='https://example.com/2',
            min_watch_time=5,
            order_index=2,
        )

    def test_course_extend_store_updates_description_and_partial_module_order(self):
        payload = {
            'description': 'Updated description',
            'modules': [
                {'id': str(self.module_c.id), 'order_index': 1},
                {'id': str(self.module_a.id), 'order_index': 2},
            ],
        }
        response = self.client.patch(
            f'/api/courses/{self.course.id}/extend-store/',
            payload,
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'success')
        self.assertIn('modules', response.data['data'])
        self.course.refresh_from_db()
        self.assertEqual(self.course.description, 'Updated description')
        # partial reorder: b should keep previous order_index=2 (after normalization it may tie, but index stays)
        self.module_a.refresh_from_db()
        self.module_b.refresh_from_db()
        self.module_c.refresh_from_db()
        # c and a get payload order_index values, b unchanged
        self.assertEqual(self.module_c.order_index, 1)
        self.assertEqual(self.module_a.order_index, 2)
        self.assertEqual(self.module_b.order_index, 2)

    def test_module_extend_store_updates_title_and_partial_lesson_order(self):
        payload = {
            'title': 'New title',
            'lessons': [
                {'id': str(self.lesson_a2.id), 'order_index': 1},
            ],
        }
        response = self.client.patch(
            f'/api/modules/{self.module_a.id}/extend-store/',
            payload,
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'success')
        self.module_a.refresh_from_db()
        self.assertEqual(self.module_a.title, 'New title')
        self.lesson_a1.refresh_from_db()
        self.lesson_a2.refresh_from_db()
        self.assertEqual(self.lesson_a2.order_index, 1)
        # partial reorder: omitted children keep existing order_index
        self.assertEqual(self.lesson_a1.order_index, 1)

    def test_course_extend_store_rejects_duplicate_module_ids(self):
        payload = {
            'modules': [
                {'id': str(self.module_a.id), 'order_index': 1},
                {'id': str(self.module_a.id), 'order_index': 2},
            ],
        }
        response = self.client.patch(
            f'/api/courses/{self.course.id}/extend-store/',
            payload,
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['code'], 603)

    def test_module_extend_store_rejects_lesson_from_other_module_and_rolls_back_title(self):
        other_module = Module.objects.create(course=self.course, title='Other', order_index=10)
        lesson_other = Lesson.objects.create(
            module=other_module,
            title='Other lesson',
            lesson_type=LESSON_TYPE_LESSON,
            content_markdown='z',
            video_url='https://example.com/3',
            min_watch_time=5,
            order_index=1,
        )
        original_title = self.module_a.title
        payload = {
            'title': 'Should not persist',
            'lessons': [
                {'id': str(lesson_other.id), 'order_index': 1},
            ],
        }
        response = self.client.patch(
            f'/api/modules/{self.module_a.id}/extend-store/',
            payload,
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['code'], 603)
        self.module_a.refresh_from_db()
        self.assertEqual(self.module_a.title, original_title)

    def test_student_cannot_call_course_extend_store(self):
        self.client.force_authenticate(user=self.student)
        response = self.client.patch(
            f'/api/courses/{self.course.id}/extend-store/',
            {'description': 'x'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_student_cannot_call_module_extend_store(self):
        self.client.force_authenticate(user=self.student)
        response = self.client.patch(
            f'/api/modules/{self.module_a.id}/extend-store/',
            {'title': 'x'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)



@override_settings(MEDIA_ROOT='/tmp/memo-test-media')
class LessonVideoPlaybackAPITestCase(APITestCase):
    def setUp(self):
        self.password = 'Password@123'
        self.admin = User.objects.create_user(
            email='admin-video@example.com',
            username='admin-video',
            password=self.password,
            role=ROLE_ADMIN,
        )
        self.student = User.objects.create_user(
            email='student-video@example.com',
            username='student-video',
            password=self.password,
            role=ROLE_STUDENT,
        )
        self.other_student = User.objects.create_user(
            email='other-student-video@example.com',
            username='other-student-video',
            password=self.password,
            role=ROLE_STUDENT,
        )
        self.course = Course.objects.create(
            title='Video Course',
            description='Video tests',
            status=COURSE_STATUS_PUBLISHED,
            created_by=self.admin,
        )
        self.module = Module.objects.create(course=self.course, title='Module', order_index=1)
        self.lesson = Lesson.objects.create(
            module=self.module,
            title='Video Lesson',
            lesson_type=LESSON_TYPE_LESSON,
            video_url='',
            content_markdown='Summary',
            min_watch_time=5,
            order_index=1,
        )
        CourseEnrollment.objects.create(user=self.student, course=self.course)

    @patch('apps.les.services.lesson_video_transcription_scheduling_service.process_lesson_video_transcription.delay')
    def test_admin_create_lesson_with_video_file(self, mock_delay):
        self.client.force_authenticate(user=self.admin)
        video_content = b'\x00' * 1024
        response = self.client.post(
            '/api/lessons/',
            {
                'module': str(self.module.id),
                'title': 'Uploaded Video Lesson',
                'lesson_type': LESSON_TYPE_LESSON,
                'content_markdown': 'Summary',
                'video_file': SimpleUploadedFile('sample.mp4', video_content, content_type='video/mp4'),
                'transcript_text': 'Manual transcript from admin upload.',
                'order_index': 2,
                'min_watch_time': 10,
            },
            format='multipart',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created = Lesson.objects.get(id=response.data['data']['id'])
        self.assertTrue(bool(created.video_file))
        self.assertEqual(created.transcript_status, TRANSCRIPT_STATUS_READY)
        self.assertEqual(created.transcript_text, 'Manual transcript from admin upload.')
        mock_delay.assert_not_called()

    def test_create_video_file_without_manual_transcript_rejected_when_auto_stt_disabled(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            '/api/lessons/',
            {
                'module': str(self.module.id),
                'title': 'Missing Transcript',
                'lesson_type': LESSON_TYPE_LESSON,
                'content_markdown': 'Summary',
                'video_file': SimpleUploadedFile('sample.mp4', b'\x00' * 1024, content_type='video/mp4'),
                'order_index': 2,
                'min_watch_time': 10,
            },
            format='multipart',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['code'], 603)

    def test_create_video_lesson_with_transcript_file_txt(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            '/api/lessons/',
            {
                'module': str(self.module.id),
                'title': 'Transcript From File',
                'lesson_type': LESSON_TYPE_LESSON,
                'content_markdown': 'Summary',
                'video_file': SimpleUploadedFile('sample.mp4', b'\x00' * 1024, content_type='video/mp4'),
                'transcript_file': SimpleUploadedFile('transcript.txt', b'Line 1\nLine 2', content_type='text/plain'),
                'order_index': 2,
                'min_watch_time': 10,
            },
            format='multipart',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created = Lesson.objects.get(id=response.data['data']['id'])
        self.assertEqual(created.transcript_text, 'Line 1\nLine 2')
        self.assertEqual(created.transcript_status, TRANSCRIPT_STATUS_READY)

    def test_create_video_lesson_with_both_transcript_text_and_file_prioritizes_file(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            '/api/lessons/',
            {
                'module': str(self.module.id),
                'title': 'Transcript Priority',
                'lesson_type': LESSON_TYPE_LESSON,
                'content_markdown': 'Summary',
                'video_file': SimpleUploadedFile('sample.mp4', b'\x00' * 1024, content_type='video/mp4'),
                'transcript_text': 'text input should be ignored',
                'transcript_file': SimpleUploadedFile('transcript.txt', b'file transcript wins', content_type='text/plain'),
                'order_index': 2,
                'min_watch_time': 10,
            },
            format='multipart',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created = Lesson.objects.get(id=response.data['data']['id'])
        self.assertEqual(created.transcript_text, 'file transcript wins')
        self.assertEqual(created.transcript_status, TRANSCRIPT_STATUS_READY)

    def test_create_video_lesson_with_empty_transcript_file_rejected(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            '/api/lessons/',
            {
                'module': str(self.module.id),
                'title': 'Empty Transcript File',
                'lesson_type': LESSON_TYPE_LESSON,
                'content_markdown': 'Summary',
                'video_file': SimpleUploadedFile('sample.mp4', b'\x00' * 1024, content_type='video/mp4'),
                'transcript_file': SimpleUploadedFile('transcript.txt', b'   ', content_type='text/plain'),
                'order_index': 2,
                'min_watch_time': 10,
            },
            format='multipart',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['code'], 603)

    def test_create_video_lesson_with_invalid_transcript_file_rejected(self):
        self.client.force_authenticate(user=self.admin)
        bad_extension_response = self.client.post(
            '/api/lessons/',
            {
                'module': str(self.module.id),
                'title': 'Bad Transcript Extension',
                'lesson_type': LESSON_TYPE_LESSON,
                'content_markdown': 'Summary',
                'video_file': SimpleUploadedFile('sample.mp4', b'\x00' * 1024, content_type='video/mp4'),
                'transcript_file': SimpleUploadedFile('transcript.md', b'hello', content_type='text/plain'),
                'order_index': 2,
                'min_watch_time': 10,
            },
            format='multipart',
        )
        self.assertEqual(bad_extension_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(bad_extension_response.data['code'], 603)

        non_utf8_response = self.client.post(
            '/api/lessons/',
            {
                'module': str(self.module.id),
                'title': 'Non UTF8 Transcript',
                'lesson_type': LESSON_TYPE_LESSON,
                'content_markdown': 'Summary',
                'video_file': SimpleUploadedFile('sample.mp4', b'\x00' * 1024, content_type='video/mp4'),
                'transcript_file': SimpleUploadedFile('transcript.txt', b'\xff\xfe', content_type='text/plain'),
                'order_index': 2,
                'min_watch_time': 10,
            },
            format='multipart',
        )
        self.assertEqual(non_utf8_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(non_utf8_response.data['code'], 603)

    def test_quiz_rejects_video_file(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            '/api/lessons/',
            {
                'module': str(self.module.id),
                'title': 'Quiz with video',
                'lesson_type': LESSON_TYPE_QUIZ,
                'quiz_questions': [
                    {'question': 'Q1', 'options': ['A', 'B', 'C', 'D'], 'correct_index': 0},
                ],
                'video_file': SimpleUploadedFile('sample.mp4', b'\x00' * 64, content_type='video/mp4'),
            },
            format='multipart',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_quiz_rejects_transcript_fields(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            '/api/lessons/',
            {
                'module': str(self.module.id),
                'title': 'Quiz with transcript',
                'lesson_type': LESSON_TYPE_QUIZ,
                'quiz_questions': [
                    {'question': 'Q1', 'options': ['A', 'B', 'C', 'D'], 'correct_index': 0},
                ],
                'transcript_text': 'Should reject',
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch('apps.les.services.lesson_video_transcription_scheduling_service.process_lesson_video_transcription.delay')
    def test_update_video_retriggers_transcript(self, mock_delay):
        self.client.force_authenticate(user=self.admin)
        self.lesson.transcript_status = 'ready'
        self.lesson.transcript_text = 'old transcript'
        self.lesson.save(update_fields=['transcript_status', 'transcript_text', 'updated_at'])
        response = self.client.patch(
            f'/api/lessons/{self.lesson.id}/',
            {
                'video_file': SimpleUploadedFile('new.mp4', b'\x00' * 128, content_type='video/mp4'),
                'transcript_text': 'Updated manual transcript',
            },
            format='multipart',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.lesson.refresh_from_db()
        self.assertEqual(self.lesson.transcript_status, TRANSCRIPT_STATUS_READY)
        self.assertEqual(self.lesson.transcript_text, 'Updated manual transcript')
        mock_delay.assert_not_called()

    @patch('apps.les.tasks.process_lesson_ingestion_job.delay')
    @patch('apps.les.tasks.transcribe_lesson_video', side_effect=RuntimeError('upstream stt connection failed'))
    def test_transcript_provider_exception_marks_lesson_failed_without_ingestion(
        self,
        _mock_transcribe,
        mock_ingestion_delay,
    ):
        self.lesson.video_file = SimpleUploadedFile('transcript-fail.mp4', b'\x00' * 256, content_type='video/mp4')
        self.lesson.transcript_status = TRANSCRIPT_STATUS_NOT_STARTED
        self.lesson.publication_status = PUBLICATION_STATUS_PROCESSING
        self.lesson.is_active = False
        self.lesson.save(update_fields=['video_file', 'transcript_status', 'publication_status', 'is_active', 'updated_at'])

        process_lesson_video_transcription.run(str(self.lesson.id))
        self.lesson.refresh_from_db()

        self.assertEqual(self.lesson.transcript_status, TRANSCRIPT_STATUS_FAILED)
        self.assertEqual(self.lesson.transcript_error, 'Lesson video transcription failed.')
        self.assertEqual(self.lesson.publication_status, PUBLICATION_STATUS_FAILED)
        self.assertFalse(self.lesson.is_active)
        self.assertEqual(LessonIngestionJob.objects.filter(lesson=self.lesson).count(), 0)
        mock_ingestion_delay.assert_not_called()

    @patch('apps.les.tasks.process_lesson_ingestion_job.delay')
    @patch('apps.les.tasks.transcribe_lesson_video', return_value='Uploaded lesson transcript')
    def test_transcript_success_enqueues_ingestion_after_video_upload(
        self,
        _mock_transcribe,
        mock_ingestion_delay,
    ):
        self.lesson.video_file = SimpleUploadedFile('transcript-ok.mp4', b'\x00' * 256, content_type='video/mp4')
        self.lesson.transcript_status = TRANSCRIPT_STATUS_NOT_STARTED
        self.lesson.publication_status = PUBLICATION_STATUS_PROCESSING
        self.lesson.is_active = False
        self.lesson.save(update_fields=['video_file', 'transcript_status', 'publication_status', 'is_active', 'updated_at'])

        process_lesson_video_transcription.run(str(self.lesson.id))
        self.lesson.refresh_from_db()

        self.assertEqual(self.lesson.transcript_status, TRANSCRIPT_STATUS_READY)
        self.assertEqual(self.lesson.transcript_text, 'Uploaded lesson transcript')
        mock_ingestion_delay.assert_called_once()
        self.assertEqual(LessonIngestionJob.objects.filter(lesson=self.lesson).count(), 1)

    def test_enrolled_user_can_get_playback_and_stream_with_range(self):
        self.lesson.video_file = SimpleUploadedFile('playback.mp4', b'0123456789' * 50, content_type='video/mp4')
        self.lesson.save(update_fields=['video_file', 'updated_at'])
        self.client.force_authenticate(user=self.student)
        metadata_response = self.client.get(f'/api/lessons/{self.lesson.id}/video/playback/')
        self.assertEqual(metadata_response.status_code, status.HTTP_200_OK)
        stream_url = metadata_response.data['data']['stream_url']
        self.assertTrue(stream_url.startswith('http://testserver/api/lessons/'))

        stream_path = urlparse(stream_url).path
        stream_query = urlparse(stream_url).query
        playback_cookie_header = '; '.join(
            f'{key}={morsel.value}' for key, morsel in self.client.cookies.items()
        )
        self.assertTrue(playback_cookie_header, msg='playback response should set HttpOnly playback cookie')
        self.client.force_authenticate(user=None)
        stream_response = self.client.get(
            f'{stream_path}?{stream_query}',
            HTTP_RANGE='bytes=0-19',
            HTTP_COOKIE=playback_cookie_header,
        )

        self.assertEqual(stream_response.status_code, status.HTTP_206_PARTIAL_CONTENT)
        self.assertEqual(stream_response['Accept-Ranges'], 'bytes')
        self.assertIn('Content-Range', stream_response)

    def test_non_enrolled_user_cannot_get_playback_metadata(self):
        self.lesson.video_file = SimpleUploadedFile('playback.mp4', b'0123456789', content_type='video/mp4')
        self.lesson.save(update_fields=['video_file', 'updated_at'])
        self.client.force_authenticate(user=self.other_student)
        response = self.client.get(f'/api/lessons/{self.lesson.id}/video/playback/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data['code'], 602)

    def test_stream_replay_without_playback_cookie_is_forbidden(self):
        self.lesson.video_file = SimpleUploadedFile('playback.mp4', b'0123456789' * 20, content_type='video/mp4')
        self.lesson.save(update_fields=['video_file', 'updated_at'])
        self.client.force_authenticate(user=self.student)
        metadata_response = self.client.get(f'/api/lessons/{self.lesson.id}/video/playback/')
        stream_url = metadata_response.data['data']['stream_url']
        parsed = urlparse(stream_url)
        self.client.cookies.clear()
        self.client.force_authenticate(user=None)
        stream_response = self.client.get(f'{parsed.path}?{parsed.query}')
        self.assertEqual(stream_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_stream_replay_with_other_user_cookie_is_forbidden(self):
        self.lesson.video_file = SimpleUploadedFile('playback.mp4', b'0123456789' * 20, content_type='video/mp4')
        self.lesson.save(update_fields=['video_file', 'updated_at'])
        self.client.force_authenticate(user=self.student)
        metadata_response = self.client.get(f'/api/lessons/{self.lesson.id}/video/playback/')
        stream_url = metadata_response.data['data']['stream_url']
        parsed = urlparse(stream_url)

        # Replace playback cookie with another enrolled user's cookie.
        self.client.force_authenticate(user=self.admin)
        self.client.get(f'/api/lessons/{self.lesson.id}/video/playback/')
        self.client.force_authenticate(user=None)
        stream_response = self.client.get(f'{parsed.path}?{parsed.query}')
        self.assertEqual(stream_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_stream_is_forbidden_when_lesson_inactive_even_with_valid_cookie(self):
        self.lesson.video_file = SimpleUploadedFile('playback.mp4', b'0123456789' * 20, content_type='video/mp4')
        self.lesson.save(update_fields=['video_file', 'updated_at'])
        self.client.force_authenticate(user=self.student)
        metadata_response = self.client.get(f'/api/lessons/{self.lesson.id}/video/playback/')
        self.assertEqual(metadata_response.status_code, status.HTTP_200_OK)
        stream_url = metadata_response.data['data']['stream_url']
        parsed = urlparse(stream_url)
        playback_cookie_header = '; '.join(
            f'{key}={morsel.value}' for key, morsel in self.client.cookies.items()
        )

        self.lesson.is_active = False
        self.lesson.save(update_fields=['is_active', 'updated_at'])

        self.client.force_authenticate(user=None)
        stream_response = self.client.get(
            f'{parsed.path}?{parsed.query}',
            HTTP_COOKIE=playback_cookie_header,
        )
        self.assertEqual(stream_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(stream_response.data['code'], 602)

    def test_lesson_detail_does_not_expose_video_file_path(self):
        self.lesson.video_file = SimpleUploadedFile('hidden.mp4', b'0123456789', content_type='video/mp4')
        self.lesson.save(update_fields=['video_file', 'updated_at'])
        self.client.force_authenticate(user=self.student)
        response = self.client.get(f'/api/lessons/{self.lesson.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('video_file', response.data['data'])
