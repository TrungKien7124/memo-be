from django.db import models
from django.utils import timezone

from apps.app_server.models.base.base_model import BaseModel


class CardSRSState(BaseModel):
    card = models.OneToOneField(
        'app_server.Flashcard',
        on_delete=models.CASCADE,
        related_name='srs_state',
    )
    stage = models.PositiveIntegerField(default=0)
    interval_days = models.PositiveIntegerField(default=1)
    due_date = models.DateField(default=timezone.now, db_index=True)
    last_review = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'card_srs_states'
        ordering = ['due_date']
        indexes = [
            models.Index(fields=['due_date'], name='idx_srs_due_date'),
        ]

    def __str__(self):
        return f'SRS({self.card.front_text[:30]}) stage={self.stage}'
