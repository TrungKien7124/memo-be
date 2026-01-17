from __future__ import annotations

from django.urls import include, path

from apps.app_server.routes.base.app_server_base_router import CoreRouter
from apps.srs.controllers.implemented.srs_health_controller import SRSHealthView
from apps.srs.controllers.implemented.srs_card_srs_state_controller import CardSRSStateViewSet

router = CoreRouter()

router.register("card-srs", CardSRSStateViewSet, basename="card-srs")

urlpatterns = [
    path("health/", SRSHealthView.as_view(), name="srs-health"),
    path("", include(router.urls)),
]
