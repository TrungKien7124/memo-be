from __future__ import annotations

from apps.app_server.serializers.base.app_server_base_serializer import AppServerBaseSerializer
from apps.app_server.validators.base.app_server_base_validator import RequiredValidator
from apps.app_server.models.implemented.cms_lesson_model import Lesson


class LessonSerializer(AppServerBaseSerializer):
    field_list = ["id", "module", "title", "video_url", "min_watch_time"]
    ignore_fields = []
    validation_rules = {
        "module": RequiredValidator(),
        "title": RequiredValidator(),
        "video_url": RequiredValidator(),
        "min_watch_time": RequiredValidator(),
    }

    class Meta(AppServerBaseSerializer.Meta):
        model = Lesson
