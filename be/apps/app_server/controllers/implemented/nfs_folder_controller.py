from __future__ import annotations

from apps.app_server.controllers.base.app_server_base_controller import AppServerBaseController

from apps.app_server.models.implemented.nfs_folder_model import Folder
from apps.app_server.normalizers import FolderInputNormalizer
from apps.app_server.serializers import FolderSerializer


class FolderViewSet(AppServerBaseController):
    model = Folder
    serializer_class = FolderSerializer
    input_normalizer_class = FolderInputNormalizer
