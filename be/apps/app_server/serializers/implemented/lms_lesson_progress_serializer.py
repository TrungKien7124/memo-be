from __future__ import annotations

from apps.app_server.serializers.base.app_server_base_serializer import AppServerBaseSerializer
from apps.app_server.validators.base.app_server_base_validator import RequiredValidator
from apps.app_server.models.implemented.lms_lesson_progress_model import LessonProgress


class LessonProgressSerializer(AppServerBaseSerializer):
    field_list = ["id", "user", "lesson", "watched_seconds", "completed", "completed_at"]
    ignore_fields = []
    validation_rules = {
        "user": RequiredValidator(),
        "lesson": RequiredValidator(),
        "watched_seconds": RequiredValidator(),
    }

    class Meta(AppServerBaseSerializer.Meta):
        model = LessonProgress
