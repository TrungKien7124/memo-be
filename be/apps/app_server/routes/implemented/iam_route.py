from __future__ import annotations

from django.urls import include, path

from apps.app_server.routes.base.app_server_base_router import CoreRouter
from apps.app_server.controllers.implemented.iam_health_controller import IAMHealthView
from apps.app_server.controllers.implemented.iam_user_controller import UserViewSet
from apps.app_server.controllers.implemented.iam_user_profile_controller import UserProfileViewSet

router = CoreRouter()

router.register("users", UserViewSet, basename="users")
router.register("profiles", UserProfileViewSet, basename="profiles")

urlpatterns = [
    path("health/", IAMHealthView.as_view(), name="iam-health"),
    path("", include(router.urls)),
]
