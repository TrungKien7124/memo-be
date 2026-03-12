from rest_framework import serializers

from apps.app_server.serializers.base.base_serializer import CoreModelSerializer
from apps.app_server.models.implemented.nfs_folder_model import Folder


class FolderSerializer(CoreModelSerializer):
    flashcard_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Folder
        fields = ['id', 'name', 'flashcard_count', 'created_at', 'updated_at']
        read_only_fields = ['id', 'flashcard_count', 'created_at', 'updated_at']
