from __future__ import annotations

from apps.app_server.serializers.base.app_server_base_serializer import AppServerBaseSerializer
from apps.app_server.validators.base.app_server_base_validator import RequiredValidator
from apps.app_server.models.implemented.iam_user_profile_model import UserProfile


class UserProfileSerializer(AppServerBaseSerializer):
    field_list = ["user", "display_name", "avatar_url", "timezone"]
    ignore_fields = []
    validation_rules = {
        "user": RequiredValidator(),
        "display_name": RequiredValidator(),
        "timezone": RequiredValidator(),
    }

    class Meta(AppServerBaseSerializer.Meta):
        model = UserProfile
