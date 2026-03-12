from apps.app_server.serializers.base.base_serializer import CoreModelSerializer
from apps.app_server.models.implemented.cms_module_model import Module


class ModuleSerializer(CoreModelSerializer):
    class Meta:
        model = Module
        fields = ['id', 'course', 'title', 'order_index', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
