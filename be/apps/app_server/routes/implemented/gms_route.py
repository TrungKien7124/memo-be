from __future__ import annotations

from django.urls import include, path

from apps.app_server.routes.base.app_server_base_router import CoreRouter
from apps.app_server.controllers.implemented.gms_health_controller import GMSHealthView

router = CoreRouter()


urlpatterns = [
    path("health/", GMSHealthView.as_view(), name="gms-health"),
    path("", include(router.urls)),
]
