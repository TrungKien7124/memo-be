from __future__ import annotations

from django.urls import include, path

from apps.app_server.routes.base.app_server_base_router import CoreRouter
from apps.ai.controllers.implemented.sps_health_controller import SPSHealthView

router = CoreRouter()

urlpatterns = [
    path("health/", SPSHealthView.as_view(), name="sps-health"),
    path("", include(router.urls)),
]
