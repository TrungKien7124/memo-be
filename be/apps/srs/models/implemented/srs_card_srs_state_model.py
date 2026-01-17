from __future__ import annotations

from django.db import models

from apps.app_server.models.base.app_server_base_model import AppServerBaseModel

from apps.app_server.models.implemented.nfs_flashcard_model import Flashcard


class CardSRSState(AppServerBaseModel):
    card = models.OneToOneField(
        Flashcard,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="srs_state",
        db_column="card_id",
    )
    stage = models.IntegerField()
    interval_days = models.IntegerField()
    due_date = models.DateField()
    last_review_date = models.DateField(blank=True, null=True)

    class Meta:
        db_table = "card_srs_state"

    def __str__(self) -> str:
        return f"{self.card_id}:{self.stage}"
