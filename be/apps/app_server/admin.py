from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from apps.app_server.models.implemented.iam_user_model import User
from apps.app_server.models.implemented.iam_user_profile_model import UserProfile
from apps.app_server.models.implemented.cms_course_model import Course
from apps.app_server.models.implemented.cms_module_model import Module
from apps.app_server.models.implemented.cms_lesson_model import Lesson
from apps.app_server.models.implemented.lms_lesson_progress_model import LessonProgress
from apps.app_server.models.implemented.nfs_folder_model import Folder
from apps.app_server.models.implemented.nfs_flashcard_model import Flashcard
from apps.app_server.models.implemented.gms_xp_transaction_model import XPTransaction
from apps.app_server.models.implemented.gms_user_xp_model import UserXP


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['email', 'username', 'role', 'is_active', 'created_at']
    list_filter = ['role', 'is_active', 'is_deleted']
    search_fields = ['email', 'username']
    ordering = ['-created_at']
    inlines = [UserProfileInline]


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['title', 'status', 'created_by', 'created_at']
    list_filter = ['status']
    search_fields = ['title']


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ['title', 'course', 'order_index']
    list_filter = ['course']


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ['title', 'module', 'min_watch_time', 'order_index']
    list_filter = ['module__course']


@admin.register(LessonProgress)
class LessonProgressAdmin(admin.ModelAdmin):
    list_display = ['user', 'lesson', 'watched_seconds', 'completed', 'completed_at']
    list_filter = ['completed']


@admin.register(Folder)
class FolderAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'created_at']
    search_fields = ['name']


@admin.register(Flashcard)
class FlashcardAdmin(admin.ModelAdmin):
    list_display = ['front_text', 'card_type', 'folder', 'user', 'created_at']
    list_filter = ['card_type']
    search_fields = ['front_text', 'back_text']


@admin.register(XPTransaction)
class XPTransactionAdmin(admin.ModelAdmin):
    list_display = ['user', 'xp_amount', 'source', 'created_at']
    list_filter = ['source']


@admin.register(UserXP)
class UserXPAdmin(admin.ModelAdmin):
    list_display = ['user', 'total_xp', 'weekly_xp', 'monthly_xp']
    ordering = ['-total_xp']
