from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.app_server.models.base.app_server_base_model import AppServerBaseModel



class Course(AppServerBaseModel):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=50)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="courses_created",
        db_column="created_by",
    )

    class Meta:
        db_table = "courses"

    def __str__(self) -> str:
        return self.title
