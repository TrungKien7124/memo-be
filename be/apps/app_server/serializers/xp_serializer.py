from rest_framework import serializers

from apps.app_server.serializers.base_serializer import CoreModelSerializer
from apps.app_server.models.xp_transaction_model import XPTransaction
from apps.app_server.models.user_xp_model import UserXP


class XPTransactionSerializer(CoreModelSerializer):
    class Meta:
        model = XPTransaction
        fields = ['id', 'xp_amount', 'source', 'source_id', 'created_at']
        read_only_fields = ['id', 'xp_amount', 'source', 'source_id', 'created_at']


class UserXPSerializer(CoreModelSerializer):
    email = serializers.EmailField(source='user.email', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = UserXP
        fields = ['id', 'email', 'username', 'total_xp', 'weekly_xp', 'monthly_xp', 'updated_at']
        read_only_fields = fields
