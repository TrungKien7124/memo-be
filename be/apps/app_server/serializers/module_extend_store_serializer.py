from typing import Any

from rest_framework import serializers

from apps.app_server.models.lesson_model import Lesson
from apps.app_server.models.module_model import Module


class ModuleExtendStoreLessonItemSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    order_index = serializers.IntegerField(min_value=0, required=False, default=0)


class ModuleExtendStoreSerializer(serializers.Serializer):
    """
    Atomic payload for updating a Module plus reordering its lessons.
    """

    title = serializers.CharField(allow_blank=True, required=False)
    lessons = ModuleExtendStoreLessonItemSerializer(many=True, required=False)

    def validate_lessons(self, value: list[dict[str, Any]]) -> list[dict[str, Any]]:
        seen_ids = set()
        duplicates = set()
        for item in value:
            lesson_id = item.get("id")
            if lesson_id in seen_ids:
                duplicates.add(str(lesson_id))
            else:
                seen_ids.add(lesson_id)

        if duplicates:
            raise serializers.ValidationError(
                {
                    "duplicates": sorted(duplicates),
                    "message": "Lesson ids must be unique within payload.",
                },
            )

        return value

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        module: Module | None = self.context.get("module")
        lessons_payload: list[dict[str, Any]] = attrs.get("lessons") or []

        if not module or not lessons_payload:
            return attrs

        lesson_ids = [item["id"] for item in lessons_payload]
        existing_ids = set(
            Lesson.objects.filter(module=module, id__in=lesson_ids).values_list("id", flat=True),
        )
        invalid_ids = [str(lid) for lid in lesson_ids if lid not in existing_ids]
        if invalid_ids:
            raise serializers.ValidationError(
                {
                    "lessons": {
                        "invalid_ids": invalid_ids,
                        "message": "All lessons must belong to the target module.",
                    },
                },
            )

        return attrs

