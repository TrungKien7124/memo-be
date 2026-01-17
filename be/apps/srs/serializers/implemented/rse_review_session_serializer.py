from __future__ import annotations

from apps.app_server.serializers.base.app_server_base_serializer import AppServerBaseSerializer
from apps.app_server.validators.base.app_server_base_validator import RequiredValidator
from apps.srs.models.implemented.rse_review_session_model import ReviewSession


class ReviewSessionSerializer(AppServerBaseSerializer):
    field_list = ["id", "user", "started_at", "ended_at"]
    ignore_fields = []
    validation_rules = {
        "user": RequiredValidator(),
    }

    class Meta(AppServerBaseSerializer.Meta):
        model = ReviewSession
