from typing import Any

from rest_framework import serializers

from apps.app_server.models.course_model import COURSE_STATUS_CHOICES, Course
from apps.app_server.models.module_model import Module


class CourseExtendStoreModuleItemSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    order_index = serializers.IntegerField(min_value=0, required=False, default=0)


class CourseExtendStoreSerializer(serializers.Serializer):
    """
    Atomic payload for updating a Course plus reordering its modules.

    This serializer only validates shape, duplicate IDs, and basic field
    constraints. The view is responsible for checking that module IDs belong to
    the given course and for applying the transaction.
    """

    description = serializers.CharField(allow_blank=True, required=False)
    status = serializers.ChoiceField(
        choices=COURSE_STATUS_CHOICES,
        required=False,
    )
    title = serializers.CharField(allow_blank=True, required=False)
    thumbnail_url = serializers.CharField(allow_blank=True, required=False)
    modules = CourseExtendStoreModuleItemSerializer(many=True, required=False)

    def validate_modules(self, value: list[dict[str, Any]]) -> list[dict[str, Any]]:
        seen_ids = set()
        duplicates = set()
        for item in value:
            module_id = item.get("id")
            if module_id in seen_ids:
                duplicates.add(str(module_id))
            else:
                seen_ids.add(module_id)

        if duplicates:
            raise serializers.ValidationError(
                {
                    "duplicates": sorted(duplicates),
                    "message": "Module ids must be unique within payload.",
                },
            )

        return value

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        course: Course | None = self.context.get("course")
        modules_payload: list[dict[str, Any]] = attrs.get("modules") or []

        if not course or not modules_payload:
            return attrs

        module_ids = [item["id"] for item in modules_payload]
        existing_ids = set(
            Module.objects.filter(course=course, id__in=module_ids).values_list("id", flat=True),
        )
        invalid_ids = [str(mid) for mid in module_ids if mid not in existing_ids]
        if invalid_ids:
            raise serializers.ValidationError(
                {
                    "modules": {
                        "invalid_ids": invalid_ids,
                        "message": "All modules must belong to the target course.",
                    },
                },
            )

        return attrs

