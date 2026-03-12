from django.urls import path, include

from apps.app_server.routes.base.base_route import BaseRouter
from apps.srs.controllers.srs_card_srs_state_controller import CardSRSStateViewSet
from apps.srs.controllers.rse_review_session_controller import ReviewSessionViewSet
from apps.srs.controllers.rse_card_review_log_controller import (
    CardReviewLogCreateView,
    CardReviewLogListView,
)

router = BaseRouter()
router.register('srs/card-srs', CardSRSStateViewSet, basename='card-srs')
router.register('rse/review-sessions', ReviewSessionViewSet, basename='review-sessions')

urlpatterns = router.urls + [
    path('rse/card-review-logs/', CardReviewLogCreateView.as_view(), name='card-review-log-create'),
    path('rse/card-review-logs/list/', CardReviewLogListView.as_view(), name='card-review-log-list'),
]
