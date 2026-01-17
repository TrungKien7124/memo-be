from __future__ import annotations

from apps.app_server.controllers.base.app_server_base_controller import AppServerBaseController

from apps.app_server.models.implemented.cms_module_model import Module
from apps.app_server.normalizers import ModuleInputNormalizer
from apps.app_server.serializers import ModuleSerializer


class ModuleViewSet(AppServerBaseController):
    model = Module
    serializer_class = ModuleSerializer
    input_normalizer_class = ModuleInputNormalizer
