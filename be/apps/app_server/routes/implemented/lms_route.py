from __future__ import annotations

from django.urls import include, path

from apps.app_server.routes.base.app_server_base_router import CoreRouter
from apps.app_server.controllers.implemented.lms_health_controller import LMSHealthView
from apps.app_server.controllers.implemented.lms_lesson_progress_controller import LessonProgressViewSet

router = CoreRouter()

router.register("lesson-progress", LessonProgressViewSet, basename="lesson-progress")

urlpatterns = [
    path("health/", LMSHealthView.as_view(), name="lms-health"),
    path("", include(router.urls)),
]
