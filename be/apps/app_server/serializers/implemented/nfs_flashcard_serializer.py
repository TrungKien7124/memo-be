from __future__ import annotations

from apps.app_server.serializers.base.app_server_base_serializer import AppServerBaseSerializer
from apps.app_server.validators.base.app_server_base_validator import RequiredValidator
from apps.app_server.models.implemented.nfs_flashcard_model import Flashcard


class FlashcardSerializer(AppServerBaseSerializer):
    field_list = [
        "id",
        "user",
        "folder",
        "front_text",
        "back_text",
        "ipa",
        "audio_url",
        "image_url",
        "card_type",
        "created_at",
    ]
    ignore_fields = []
    validation_rules = {
        "user": RequiredValidator(),
        "folder": RequiredValidator(),
        "front_text": RequiredValidator(),
        "back_text": RequiredValidator(),
        "card_type": RequiredValidator(),
    }

    class Meta(AppServerBaseSerializer.Meta):
        model = Flashcard
