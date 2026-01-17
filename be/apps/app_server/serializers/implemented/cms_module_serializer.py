from __future__ import annotations

from apps.app_server.serializers.base.app_server_base_serializer import AppServerBaseSerializer
from apps.app_server.validators.base.app_server_base_validator import RequiredValidator
from apps.app_server.models.implemented.cms_module_model import Module


class ModuleSerializer(AppServerBaseSerializer):
    field_list = ["id", "course", "title", "order_index"]
    ignore_fields = []
    validation_rules = {
        "course": RequiredValidator(),
        "title": RequiredValidator(),
        "order_index": RequiredValidator(),
    }

    class Meta(AppServerBaseSerializer.Meta):
        model = Module
