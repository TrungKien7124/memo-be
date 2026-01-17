from __future__ import annotations

from django.urls import include, path

from apps.app_server.routes.base.app_server_base_router import CoreRouter
from apps.app_server.controllers.implemented.adm_health_controller import ADMHealthView

router = CoreRouter()


urlpatterns = [
    path("health/", ADMHealthView.as_view(), name="adm-health"),
    path("", include(router.urls)),
]
