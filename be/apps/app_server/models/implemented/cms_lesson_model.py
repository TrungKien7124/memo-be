from __future__ import annotations

from django.db import models

from apps.app_server.models.base.app_server_base_model import AppServerBaseModel


from apps.app_server.models.implemented.cms_module_model import Module


class Lesson(AppServerBaseModel):
    module = models.ForeignKey(
        Module,
        on_delete=models.CASCADE,
        related_name="lessons",
        db_column="module_id",
    )
    title = models.CharField(max_length=255)
    video_url = models.TextField()
    min_watch_time = models.IntegerField()

    class Meta:
        db_table = "lessons"

    def __str__(self) -> str:
        return self.title
