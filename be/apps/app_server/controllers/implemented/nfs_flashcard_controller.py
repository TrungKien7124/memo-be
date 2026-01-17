from __future__ import annotations

from apps.app_server.controllers.base.app_server_base_controller import AppServerBaseController

from apps.app_server.models.implemented.nfs_flashcard_model import Flashcard
from apps.app_server.normalizers import FlashcardInputNormalizer
from apps.app_server.serializers import FlashcardSerializer


class FlashcardViewSet(AppServerBaseController):
    model = Flashcard
    serializer_class = FlashcardSerializer
    input_normalizer_class = FlashcardInputNormalizer
