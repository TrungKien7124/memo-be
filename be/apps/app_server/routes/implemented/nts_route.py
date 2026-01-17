from __future__ import annotations

from django.urls import include, path

from apps.app_server.routes.base.app_server_base_router import CoreRouter
from apps.app_server.controllers.implemented.nts_health_controller import NTSHealthView

router = CoreRouter()


urlpatterns = [
    path("health/", NTSHealthView.as_view(), name="nts-health"),
    path("", include(router.urls)),
]
