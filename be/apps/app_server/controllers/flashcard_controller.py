from rest_framework.permissions import IsAuthenticated

from apps.app_server.controllers.base_controller import CoreModelViewSet
from apps.app_server.models.flashcard_model import Flashcard
from apps.app_server.serializers.flashcard_serializer import FlashcardSerializer
from apps.app_server.normalizers.flashcard_normalizer import FlashcardNormalizer


class FlashcardViewSet(CoreModelViewSet):
    serializer_class = FlashcardSerializer
    permission_classes = [IsAuthenticated]
    normalizer_class = FlashcardNormalizer
    filterset_fields = ['folder', 'card_type']
    search_fields = ['front_text', 'back_text']

    def get_queryset(self):
        return Flashcard.objects.filter(user=self.request.user).select_related('folder')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
