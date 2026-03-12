from rest_framework import serializers

from apps.app_server.serializers.base.base_serializer import CoreModelSerializer
from apps.app_server.models.implemented.iam_user_profile_model import UserProfile


class UserProfileSerializer(CoreModelSerializer):
    email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = UserProfile
        fields = ['id', 'email', 'display_name', 'avatar_url', 'timezone', 'created_at', 'updated_at']
        read_only_fields = ['id', 'email', 'created_at', 'updated_at']
