from __future__ import annotations

from django.urls import include, path

from apps.app_server.routes.base.app_server_base_router import CoreRouter
from apps.app_server.controllers.implemented.cms_health_controller import CMSHealthView
from apps.app_server.controllers.implemented.cms_course_controller import CourseViewSet
from apps.app_server.controllers.implemented.cms_module_controller import ModuleViewSet
from apps.app_server.controllers.implemented.cms_lesson_controller import LessonViewSet

router = CoreRouter()

router.register("courses", CourseViewSet, basename="courses")
router.register("modules", ModuleViewSet, basename="modules")
router.register("lessons", LessonViewSet, basename="lessons")

urlpatterns = [
    path("health/", CMSHealthView.as_view(), name="cms-health"),
    path("", include(router.urls)),
]
