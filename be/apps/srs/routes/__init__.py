from django.urls import path, include

from apps.app_server.routes.base_route import BaseRouter
from apps.srs.controllers.card_repetition_state_controller import CardSRSStateViewSet
from apps.srs.controllers.review_session_controller import ReviewSessionViewSet
from apps.srs.controllers.card_review_log_controller import (
    CardReviewLogCreateView,
    CardReviewLogListView,
)

router = BaseRouter()
router.register('card-repetition-states', CardSRSStateViewSet, basename='card-repetition-states')
router.register('review-sessions', ReviewSessionViewSet, basename='review-sessions')

urlpatterns = router.urls + [
    path('card-review-logs/', CardReviewLogCreateView.as_view(), name='card-review-log-create'),
    path('card-review-logs/list/', CardReviewLogListView.as_view(), name='card-review-log-list'),
]
