from apps.app_server.serializers.base.base_serializer import CoreModelSerializer
from apps.srs.models.srs_card_srs_state_model import CardSRSState


class CardSRSStateSerializer(CoreModelSerializer):
    class Meta:
        model = CardSRSState
        fields = ['id', 'card', 'stage', 'interval_days', 'due_date', 'last_review', 'created_at', 'updated_at']
        read_only_fields = ['id', 'card', 'stage', 'interval_days', 'due_date', 'last_review', 'created_at', 'updated_at']
