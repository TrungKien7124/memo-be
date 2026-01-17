from __future__ import annotations

from django.db import models

from apps.app_server.models.base.app_server_base_model import AppServerBaseModel


from apps.app_server.models.implemented.cms_course_model import Course


class Module(AppServerBaseModel):
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="modules",
        db_column="course_id",
    )
    title = models.CharField(max_length=255)
    order_index = models.IntegerField()

    class Meta:
        db_table = "modules"

    def __str__(self) -> str:
        return self.title
