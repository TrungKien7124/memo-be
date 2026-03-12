from django.conf import settings
from django.db import models

from apps.app_server.models.base.base_model import BaseModel

CHOICE_EASY = 'EASY'
CHOICE_GOOD = 'GOOD'
CHOICE_HARD = 'HARD'

REVIEW_CHOICES = [
    (CHOICE_EASY, 'Easy'),
    (CHOICE_GOOD, 'Good'),
    (CHOICE_HARD, 'Hard'),
]


class CardReviewLog(BaseModel):
    card = models.ForeignKey(
        'app_server.Flashcard',
        on_delete=models.CASCADE,
        related_name='review_logs',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='card_review_logs',
    )
    session = models.ForeignKey(
        'srs.ReviewSession',
        on_delete=models.CASCADE,
        related_name='review_logs',
    )
    choice = models.CharField(max_length=4, choices=REVIEW_CHOICES)
    reviewed_at = models.DateTimeField(auto_now_add=True)
    prev_stage = models.PositiveIntegerField()
    new_stage = models.PositiveIntegerField()
    prev_interval = models.PositiveIntegerField()
    new_interval = models.PositiveIntegerField()
    prev_due_date = models.DateField()
    new_due_date = models.DateField()

    class Meta:
        db_table = 'card_review_logs'
        ordering = ['-reviewed_at']
        indexes = [
            models.Index(fields=['user', 'reviewed_at'], name='idx_review_log_user_date'),
        ]

    def __str__(self):
        return f'{self.choice} on {self.card.front_text[:30]}'
