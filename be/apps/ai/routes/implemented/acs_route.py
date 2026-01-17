from __future__ import annotations

from django.urls import include, path

from apps.app_server.routes.base.app_server_base_router import CoreRouter
from apps.ai.controllers.implemented.acs_health_controller import ACSHealthView

router = CoreRouter()

urlpatterns = [
    path("health/", ACSHealthView.as_view(), name="acs-health"),
    path("", include(router.urls)),
]
