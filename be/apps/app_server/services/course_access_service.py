from apps.app_server.models.course_enrollment_model import CourseEnrollment
from apps.app_server.models.user_model import ROLE_ADMIN, ROLE_STUDENT, ROLE_TEACHER


def is_admin_user(user):
    return bool(user and user.is_authenticated and user.role == ROLE_ADMIN)


def user_has_course_access(user, course_id):
    if is_admin_user(user):
        return True
    if not user or not user.is_authenticated:
        return False
    if user.role not in (ROLE_TEACHER, ROLE_STUDENT):
        return False
    return CourseEnrollment.objects.filter(user=user, course_id=course_id).exists()


def user_has_module_access(user, module_id):
    if is_admin_user(user):
        return True
    if not user or not user.is_authenticated:
        return False
    return CourseEnrollment.objects.filter(
        user=user,
        course__modules__id=module_id,
        course__modules__is_deleted=False,
    ).exists()


def user_has_lesson_access(user, lesson_id):
    if is_admin_user(user):
        return True
    if not user or not user.is_authenticated:
        return False
    return CourseEnrollment.objects.filter(
        user=user,
        course__modules__lessons__id=lesson_id,
        course__modules__is_deleted=False,
        course__modules__lessons__is_deleted=False,
    ).exists()
