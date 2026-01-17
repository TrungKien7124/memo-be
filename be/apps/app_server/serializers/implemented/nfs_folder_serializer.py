from __future__ import annotations

from apps.app_server.serializers.base.app_server_base_serializer import AppServerBaseSerializer
from apps.app_server.validators.base.app_server_base_validator import RequiredValidator
from apps.app_server.models.implemented.nfs_folder_model import Folder


class FolderSerializer(AppServerBaseSerializer):
    field_list = ["id", "user", "name"]
    ignore_fields = []
    validation_rules = {
        "user": RequiredValidator(),
        "name": RequiredValidator(),
    }

    class Meta(AppServerBaseSerializer.Meta):
        model = Folder
