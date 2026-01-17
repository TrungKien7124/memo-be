from __future__ import annotations

from django.urls import include, path

from apps.app_server.routes.base.app_server_base_router import CoreRouter
from apps.srs.controllers.implemented.rse_health_controller import RSEHealthView
from apps.srs.controllers.implemented.rse_review_session_controller import ReviewSessionViewSet
from apps.srs.controllers.implemented.rse_card_review_log_controller import CardReviewLogViewSet

router = CoreRouter()

router.register("review-sessions", ReviewSessionViewSet, basename="review-sessions")
router.register("card-review-logs", CardReviewLogViewSet, basename="card-review-logs")

urlpatterns = [
    path("health/", RSEHealthView.as_view(), name="rse-health"),
    path("", include(router.urls)),
]
