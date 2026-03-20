from rest_framework import serializers

from apps.app_server.serializers.base.base_serializer import CoreModelSerializer
from apps.srs.models.srs_card_srs_state_model import CardSRSState


class CardSRSStateSerializer(CoreModelSerializer):
    card_detail = serializers.SerializerMethodField()

    class Meta:
        model = CardSRSState
        fields = [
            'id',
            'card',
            'card_detail',
            'stage',
            'interval_days',
            'due_date',
            'last_review',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'card', 'stage', 'interval_days', 'due_date', 'last_review', 'created_at', 'updated_at']

    def get_card_detail(self, obj):
        card = obj.card
        return {
            'id': str(card.id),
            'front_text': card.front_text,
            'back_text': card.back_text,
            'ipa': card.ipa,
            'audio_url': card.audio_url,
            'image_url': card.image_url,
            'card_type': card.card_type,
        }
