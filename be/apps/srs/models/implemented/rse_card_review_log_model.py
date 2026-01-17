from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.app_server.models.base.app_server_base_model import AppServerBaseModel

from apps.app_server.models.implemented.nfs_flashcard_model import Flashcard
from apps.srs.models.implemented.rse_review_session_model import ReviewSession


class CardReviewLog(AppServerBaseModel):
    card = models.ForeignKey(
        Flashcard,
        on_delete=models.CASCADE,
        related_name="review_logs",
        db_column="card_id",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="card_review_logs",
        db_column="user_id",
    )
    session = models.ForeignKey(
        ReviewSession,
        on_delete=models.CASCADE,
        related_name="card_reviews",
        db_column="session_id",
    )
    choice = models.CharField(max_length=50)
    reviewed_at = models.DateTimeField(auto_now_add=True)
    prev_stage = models.IntegerField()
    new_stage = models.IntegerField()
    prev_interval = models.IntegerField()
    new_interval = models.IntegerField()
    prev_due_date = models.DateField()
    new_due_date = models.DateField()

    class Meta:
        db_table = "card_review_log"

    def __str__(self) -> str:
        return f"{self.card_id}:{self.reviewed_at.isoformat()}"
