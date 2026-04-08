from django.contrib.auth import get_user_model

from apps.app_server.serializers.base_serializer import CoreModelSerializer

User = get_user_model()


class UserSerializer(CoreModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'role', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'email', 'created_at', 'updated_at']
