from __future__ import annotations

from apps.app_server.serializers.base.app_server_base_serializer import AppServerBaseSerializer
from apps.app_server.validators.base.app_server_base_validator import RequiredValidator
from apps.srs.models.implemented.srs_card_srs_state_model import CardSRSState


class CardSRSStateSerializer(AppServerBaseSerializer):
    field_list = ["card", "stage", "interval_days", "due_date", "last_review_date"]
    ignore_fields = []
    validation_rules = {
        "card": RequiredValidator(),
        "stage": RequiredValidator(),
        "interval_days": RequiredValidator(),
        "due_date": RequiredValidator(),
    }

    class Meta(AppServerBaseSerializer.Meta):
        model = CardSRSState
