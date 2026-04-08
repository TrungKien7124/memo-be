from django.db.models import Sum
from rest_framework import serializers

from apps.app_server.models.xp_transaction_model import XPTransaction
from apps.app_server.serializers.base_serializer import CoreModelSerializer
from apps.srs.models.card_review_log_model import CardReviewLog
from apps.srs.models.review_session_model import ReviewSession


class ReviewSessionSerializer(CoreModelSerializer):
    cards_reviewed = serializers.SerializerMethodField()
    xp_earned = serializers.SerializerMethodField()
    folder_id = serializers.UUIDField(source='folder', allow_null=True, read_only=True)

    class Meta:
        model = ReviewSession
        fields = [
            'id',
            'user',
            'folder_id',
            'started_at',
            'ended_at',
            'created_at',
            'updated_at',
            'cards_reviewed',
            'xp_earned',
        ]
        read_only_fields = [
            'id',
            'user',
            'folder_id',
            'started_at',
            'created_at',
            'updated_at',
            'cards_reviewed',
            'xp_earned',
        ]

    def get_cards_reviewed(self, obj):
        return CardReviewLog.objects.filter(session=obj).count()

    def get_xp_earned(self, obj):
        log_ids = CardReviewLog.objects.filter(session=obj).values_list('id', flat=True)
        result = XPTransaction.objects.filter(
            user=obj.user,
            source='review',
            source_id__in=log_ids,
        ).aggregate(total=Sum('xp_amount'))
        return result['total'] or 0
