from apps.app_server.serializers.base_serializer import CoreModelSerializer
from apps.app_server.models.flashcard_model import Flashcard


class FlashcardSerializer(CoreModelSerializer):
    class Meta:
        model = Flashcard
        fields = [
            'id', 'folder', 'front_text', 'back_text', 'ipa',
            'audio_url', 'image_url', 'card_type', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
