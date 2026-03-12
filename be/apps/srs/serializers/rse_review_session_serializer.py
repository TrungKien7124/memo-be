from apps.app_server.serializers.base.base_serializer import CoreModelSerializer
from apps.srs.models.rse_review_session_model import ReviewSession


class ReviewSessionSerializer(CoreModelSerializer):
    class Meta:
        model = ReviewSession
        fields = ['id', 'user', 'started_at', 'ended_at', 'created_at', 'updated_at']
        read_only_fields = ['id', 'user', 'started_at', 'created_at', 'updated_at']
