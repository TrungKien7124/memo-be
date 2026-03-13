from rest_framework import serializers

from apps.app_server.serializers.base.base_serializer import CoreModelSerializer
from apps.app_server.models.implemented.cms_module_model import Module


class ModuleSerializer(CoreModelSerializer):
    is_unlocked = serializers.SerializerMethodField()
    is_completed = serializers.SerializerMethodField()

    def get_is_unlocked(self, obj):
        state_map = self.context.get('module_state_map', {})
        return state_map.get(obj.id, {}).get('is_unlocked', True)

    def get_is_completed(self, obj):
        state_map = self.context.get('module_state_map', {})
        return state_map.get(obj.id, {}).get('is_completed', False)

    class Meta:
        model = Module
        fields = ['id', 'course', 'title', 'order_index', 'is_unlocked', 'is_completed', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
