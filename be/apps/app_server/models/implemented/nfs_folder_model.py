from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.app_server.models.base.app_server_base_model import AppServerBaseModel



class Folder(AppServerBaseModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="folders",
        db_column="user_id",
    )
    name = models.CharField(max_length=255)

    class Meta:
        db_table = "folders"

    def __str__(self) -> str:
        return self.name
