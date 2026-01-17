from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.app_server.models.base.app_server_base_model import AppServerBaseModel


from apps.app_server.models.implemented.cms_lesson_model import Lesson


class LessonProgress(AppServerBaseModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="lesson_progress",
        db_column="user_id",
    )
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name="progress",
        db_column="lesson_id",
    )
    watched_seconds = models.IntegerField()
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = "lesson_progress"
        unique_together = ("user", "lesson")

    def __str__(self) -> str:
        return f"{self.user_id}:{self.lesson_id}"
