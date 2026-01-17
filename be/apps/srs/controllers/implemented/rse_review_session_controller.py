from __future__ import annotations

from apps.app_server.controllers.base.app_server_base_controller import AppServerBaseController

from apps.srs.models.implemented.rse_review_session_model import ReviewSession
from apps.srs.normalizers import ReviewSessionInputNormalizer
from apps.srs.serializers import ReviewSessionSerializer


class ReviewSessionViewSet(AppServerBaseController):
    model = ReviewSession
    serializer_class = ReviewSessionSerializer
    input_normalizer_class = ReviewSessionInputNormalizer
