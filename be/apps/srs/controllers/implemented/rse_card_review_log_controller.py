from __future__ import annotations

from apps.app_server.controllers.base.app_server_base_controller import AppServerBaseController

from apps.srs.models.implemented.rse_card_review_log_model import CardReviewLog
from apps.srs.normalizers import CardReviewLogInputNormalizer
from apps.srs.serializers import CardReviewLogSerializer


class CardReviewLogViewSet(AppServerBaseController):
    model = CardReviewLog
    serializer_class = CardReviewLogSerializer
    input_normalizer_class = CardReviewLogInputNormalizer
