from __future__ import annotations

from apps.app_server.controllers.base.app_server_base_controller import AppServerBaseController

from apps.app_server.models.implemented.iam_user_profile_model import UserProfile
from apps.app_server.normalizers import UserProfileInputNormalizer
from apps.app_server.serializers import UserProfileSerializer


class UserProfileViewSet(AppServerBaseController):
    model = UserProfile
    serializer_class = UserProfileSerializer
    input_normalizer_class = UserProfileInputNormalizer
