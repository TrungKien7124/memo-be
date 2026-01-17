from __future__ import annotations

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.app_server.models.implemented.cms_course_model import Course
from apps.app_server.models.implemented.cms_lesson_model import Lesson
from apps.app_server.models.implemented.cms_module_model import Module
from apps.app_server.models.implemented.iam_user_profile_model import UserProfile
from apps.app_server.models.implemented.lms_lesson_progress_model import LessonProgress
from apps.app_server.models.implemented.nfs_flashcard_model import Flashcard
from apps.app_server.models.implemented.nfs_folder_model import Folder
from apps.srs.models.implemented.rse_card_review_log_model import CardReviewLog
from apps.srs.models.implemented.rse_review_session_model import ReviewSession
from apps.srs.models.implemented.srs_card_srs_state_model import CardSRSState


class Command(BaseCommand):
    help = "Seed demo data for local development."

    def handle(self, *args, **options):
        user = self._get_or_create_user()
        profile = self._get_or_create_profile(user)
        course, module, lesson = self._get_or_create_course_tree(user)
        self._get_or_create_lesson_progress(user, lesson)
        folder, flashcard = self._get_or_create_flashcard(user)
        self._get_or_create_srs_state(flashcard)
        self._get_or_create_review_log(user, flashcard)

        self.stdout.write(self.style.SUCCESS("Seed data created."))
        self.stdout.write(f"User: {user.username} ({user.email})")
        self.stdout.write(f"Profile: {profile.display_name}")
        self.stdout.write(f"Course: {course.title} / Module: {module.title} / Lesson: {lesson.title}")
        self.stdout.write(f"Folder: {folder.name} / Flashcard: {flashcard.front_text}")

    def _get_or_create_user(self):
        User = get_user_model()
        user, created = User.objects.get_or_create(
            username="demo",
            defaults={"email": "demo@example.com", "role": "student"},
        )
        if created:
            user.set_password("demo1234")
            user.save(update_fields=["password"])
        return user

    def _get_or_create_profile(self, user):
        profile, _ = UserProfile.objects.get_or_create(
            user=user,
            defaults={"display_name": "Demo User", "timezone": "UTC"},
        )
        return profile

    def _get_or_create_course_tree(self, user):
        course, _ = Course.objects.get_or_create(
            title="English Basics",
            defaults={"description": "Starter course", "status": "active", "created_by": user},
        )
        module, _ = Module.objects.get_or_create(
            course=course,
            title="Module 1: Introductions",
            defaults={"order_index": 1},
        )
        lesson, _ = Lesson.objects.get_or_create(
            module=module,
            title="Lesson 1: Greetings",
            defaults={"video_url": "https://example.com/video", "min_watch_time": 120},
        )
        return course, module, lesson

    def _get_or_create_lesson_progress(self, user, lesson):
        LessonProgress.objects.get_or_create(
            user=user,
            lesson=lesson,
            defaults={"watched_seconds": 140, "completed": True, "completed_at": timezone.now()},
        )

    def _get_or_create_flashcard(self, user):
        folder, _ = Folder.objects.get_or_create(user=user, name="Daily Vocabulary")
        flashcard, _ = Flashcard.objects.get_or_create(
            user=user,
            folder=folder,
            front_text="hello",
            defaults={
                "back_text": "xin chao",
                "ipa": "həˈloʊ",
                "audio_url": "",
                "image_url": "",
                "card_type": "vocab",
            },
        )
        return folder, flashcard

    def _get_or_create_srs_state(self, flashcard):
        today = timezone.now().date()
        CardSRSState.objects.get_or_create(
            card=flashcard,
            defaults={"stage": 1, "interval_days": 3, "due_date": today + timedelta(days=3)},
        )

    def _get_or_create_review_log(self, user, flashcard):
        session, _ = ReviewSession.objects.get_or_create(
            user=user,
            defaults={"started_at": timezone.now()},
        )
        CardReviewLog.objects.get_or_create(
            card=flashcard,
            user=user,
            session=session,
            defaults={
                "choice": "easy",
                "reviewed_at": timezone.now(),
                "prev_stage": 0,
                "new_stage": 1,
                "prev_interval": 0,
                "new_interval": 3,
                "prev_due_date": timezone.now().date(),
                "new_due_date": timezone.now().date() + timedelta(days=3),
            },
        )
