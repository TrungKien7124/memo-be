from __future__ import annotations

from apps.app_server.serializers.base.app_server_base_serializer import AppServerBaseSerializer
from apps.app_server.validators.base.app_server_base_validator import RequiredValidator
from apps.srs.models.implemented.rse_card_review_log_model import CardReviewLog


class CardReviewLogSerializer(AppServerBaseSerializer):
    field_list = [
        "id",
        "card",
        "user",
        "session",
        "choice",
        "reviewed_at",
        "prev_stage",
        "new_stage",
        "prev_interval",
        "new_interval",
        "prev_due_date",
        "new_due_date",
    ]
    ignore_fields = []
    validation_rules = {
        "card": RequiredValidator(),
        "user": RequiredValidator(),
        "session": RequiredValidator(),
        "choice": RequiredValidator(),
        "prev_stage": RequiredValidator(),
        "new_stage": RequiredValidator(),
        "prev_interval": RequiredValidator(),
        "new_interval": RequiredValidator(),
        "prev_due_date": RequiredValidator(),
        "new_due_date": RequiredValidator(),
    }

    class Meta(AppServerBaseSerializer.Meta):
        model = CardReviewLog
