from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from apps.app_server.models.user_profile_model import UserProfile
from apps.app_server.models.course_model import Course, COURSE_STATUS_PUBLISHED
from apps.app_server.models.module_model import Module
from apps.app_server.models.lesson_model import Lesson
from apps.app_server.models.folder_model import Folder
from apps.app_server.models.flashcard_model import Flashcard
from apps.app_server.models.user_xp_model import UserXP

User = get_user_model()


class Command(BaseCommand):
    help = "Seed database with demo data for development"

    def handle(self, *args, **options):
        self.stdout.write("Seeding demo data...")

        self._ensure_demo_admin()
        teacher = self._create_user(
            "teacher@memo.dev", "teacher", "Teacher@123", "teacher"
        )
        student = self._create_user(
            "student@memo.dev", "student", "Student@123", "student"
        )

        course = self._create_course(teacher)
        self._create_flashcards(student)

        self.stdout.write(self.style.SUCCESS("Demo data seeded successfully!"))
        self.stdout.write("  Admin:   admin@memo.dev / admin (username: admin)")
        self.stdout.write("  Teacher: teacher@memo.dev / Teacher@123")
        self.stdout.write("  Student: student@memo.dev / Student@123")

    def _ensure_demo_admin(self):
        email = "admin@memo.dev"
        username = "admin"
        password = "admin"
        user = User.objects.all_with_deleted().filter(email=email).first()
        if user:
            user.username = username
            user.role = "admin"
            user.is_staff = True
            user.is_superuser = True
            user.is_active = True
            if user.is_deleted:
                user.is_deleted = False
            user.set_password(password)
            user.save()
            UserProfile.objects.get_or_create(
                user=user, defaults={"display_name": "Admin"}
            )
            UserXP.objects.get_or_create(user=user)
            self.stdout.write(
                f"  Ensured demo admin (created earlier): {email} / {password}"
            )
            return user
        return self._create_user(email, username, password, "admin")

    def _create_user(self, email, username, password, role):
        if User.objects.all_with_deleted().filter(email=email).exists():
            self.stdout.write(f"  User {email} already exists, skipping.")
            return User.objects.all_with_deleted().get(email=email)

        user = User.objects.create_user(
            email=email,
            username=username,
            password=password,
            role=role,
        )
        if role == "admin":
            user.is_staff = True
            user.is_superuser = True
            user.save()

        UserProfile.objects.create(user=user, display_name=username.capitalize())
        UserXP.objects.create(user=user)
        self.stdout.write(f"  Created user: {email} ({role})")
        return user

    def _create_course(self, teacher):
        if Course.objects.filter(title="English Basics").exists():
            self.stdout.write("  Course already exists, skipping.")
            return Course.objects.get(title="English Basics")

        course = Course.objects.create(
            title="English Basics",
            description="A beginner course to learn English fundamentals.",
            status=COURSE_STATUS_PUBLISHED,
            created_by=teacher,
        )

        for i, (mod_title, lessons) in enumerate(
            [
                (
                    "Greetings & Introductions",
                    [
                        ("Hello & Goodbye", "https://www.youtube.com/watch?v=example1"),
                        (
                            "Introducing Yourself",
                            "https://www.youtube.com/watch?v=example2",
                        ),
                    ],
                ),
                (
                    "Daily Conversations",
                    [
                        (
                            "At the Restaurant",
                            "https://www.youtube.com/watch?v=example3",
                        ),
                        ("Shopping", "https://www.youtube.com/watch?v=example4"),
                        (
                            "Asking for Directions",
                            "https://www.youtube.com/watch?v=example5",
                        ),
                    ],
                ),
            ]
        ):
            module = Module.objects.create(
                course=course, title=mod_title, order_index=i
            )
            for j, (lesson_title, video_url) in enumerate(lessons):
                Lesson.objects.create(
                    module=module,
                    title=lesson_title,
                    video_url=video_url,
                    order_index=j,
                )

        self.stdout.write(f"  Created course: {course.title}")
        return course

    def _create_flashcards(self, student):
        if Folder.objects.filter(user=student, name="Basic Vocabulary").exists():
            self.stdout.write("  Flashcards already exist, skipping.")
            return

        folder = Folder.objects.create(user=student, name="Basic Vocabulary")

        cards = [
            ("Hello", "Xin chào", "/həˈloʊ/"),
            ("Goodbye", "Tạm biệt", "/ɡʊdˈbaɪ/"),
            ("Thank you", "Cảm ơn", "/θæŋk juː/"),
            ("Please", "Làm ơn", "/pliːz/"),
            ("Sorry", "Xin lỗi", "/ˈsɒri/"),
            ("Yes", "Vâng / Có", "/jes/"),
            ("No", "Không", "/noʊ/"),
            ("Water", "Nước", "/ˈwɔːtər/"),
            ("Food", "Thức ăn", "/fuːd/"),
            ("Help", "Giúp đỡ", "/help/"),
        ]

        for front, back, ipa in cards:
            Flashcard.objects.create(
                user=student,
                folder=folder,
                front_text=front,
                back_text=back,
                ipa=ipa,
            )

        self.stdout.write(f"  Created {len(cards)} flashcards in folder: {folder.name}")
