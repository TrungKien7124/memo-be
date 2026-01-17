from __future__ import annotations

from apps.app_server.controllers.base.app_server_base_controller import AppServerBaseController

from apps.srs.models.implemented.srs_card_srs_state_model import CardSRSState
from apps.srs.normalizers import CardSRSStateInputNormalizer
from apps.srs.serializers import CardSRSStateSerializer


class CardSRSStateViewSet(AppServerBaseController):
    model = CardSRSState
    serializer_class = CardSRSStateSerializer
    input_normalizer_class = CardSRSStateInputNormalizer
