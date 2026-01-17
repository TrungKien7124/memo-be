from __future__ import annotations

from apps.app_server.controllers.base.app_server_base_controller import AppServerBaseController

from apps.app_server.models.implemented.iam_user_model import User
from apps.app_server.normalizers import UserInputNormalizer
from apps.app_server.serializers import UserSerializer


class UserViewSet(AppServerBaseController):
    model = User
    serializer_class = UserSerializer
    input_normalizer_class = UserInputNormalizer
