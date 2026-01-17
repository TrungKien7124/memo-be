from __future__ import annotations

from apps.app_server.serializers.base.app_server_base_serializer import AppServerBaseSerializer
from apps.app_server.validators.base.app_server_base_validator import RequiredValidator
from apps.app_server.models.implemented.cms_course_model import Course


class CourseSerializer(AppServerBaseSerializer):
    field_list = ["id", "title", "description", "status", "created_by"]
    ignore_fields = []
    validation_rules = {
        "title": RequiredValidator(),
        "status": RequiredValidator(),
        "created_by": RequiredValidator(),
    }

    class Meta(AppServerBaseSerializer.Meta):
        model = Course
