from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.app_server.models.base.app_server_base_model import AppServerBaseModel


class ReviewSession(AppServerBaseModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="review_sessions",
        db_column="user_id",
    )
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = "review_sessions"

    def __str__(self) -> str:
        return f"{self.user_id}:{self.started_at.isoformat()}"
