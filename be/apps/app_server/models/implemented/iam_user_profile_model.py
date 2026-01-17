from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.app_server.models.base.app_server_base_model import AppServerBaseModel



class UserProfile(AppServerBaseModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="profile",
        db_column="user_id",
    )
    display_name = models.CharField(max_length=255)
    avatar_url = models.TextField(blank=True, null=True)
    timezone = models.CharField(max_length=64)

    class Meta:
        db_table = "user_profile"

    def __str__(self) -> str:
        return self.display_name
