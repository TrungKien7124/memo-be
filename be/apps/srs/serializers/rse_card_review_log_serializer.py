from rest_framework import serializers

from apps.app_server.serializers.base.base_serializer import CoreModelSerializer
from apps.srs.models.rse_card_review_log_model import CardReviewLog


class CardReviewLogSerializer(CoreModelSerializer):
    class Meta:
        model = CardReviewLog
        fields = [
            'id', 'card', 'user', 'session', 'choice', 'reviewed_at',
            'prev_stage', 'new_stage', 'prev_interval', 'new_interval',
            'prev_due_date', 'new_due_date', 'created_at',
        ]
        read_only_fields = [
            'id', 'user', 'reviewed_at',
            'prev_stage', 'new_stage', 'prev_interval', 'new_interval',
            'prev_due_date', 'new_due_date', 'created_at',
        ]


class CardReviewLogCreateSerializer(serializers.Serializer):
    card = serializers.UUIDField()
    session = serializers.UUIDField()
    choice = serializers.ChoiceField(choices=['EASY', 'GOOD', 'HARD'])
