from __future__ import annotations

from django.urls import include, path

from apps.app_server.routes.base.app_server_base_router import CoreRouter
from apps.app_server.controllers.implemented.soc_health_controller import SOCHealthView

router = CoreRouter()


urlpatterns = [
    path("health/", SOCHealthView.as_view(), name="soc-health"),
    path("", include(router.urls)),
]
