from __future__ import annotations

from apps.app_server.serializers.base.app_server_base_serializer import AppServerBaseSerializer
from apps.app_server.validators.base.app_server_base_validator import RequiredValidator
from apps.app_server.models.implemented.iam_user_model import User


class UserSerializer(AppServerBaseSerializer):
    field_list = [
        "id",
        "username",
        "email",
        "password",
        "role",
        "is_active",
        "is_staff",
        "date_joined",
        "last_login",
    ]
    ignore_fields = []
    validation_rules = {
        "username": RequiredValidator(),
        "email": RequiredValidator(),
    }

    class Meta(AppServerBaseSerializer.Meta):
        model = User
        extra_kwargs = {
            "password": {"write_only": True, "required": False},
            "last_login": {"read_only": True},
            "date_joined": {"read_only": True},
        }

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        user = User(**validated_data)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance
