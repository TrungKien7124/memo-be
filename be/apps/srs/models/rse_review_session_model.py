from django.conf import settings
from django.db import models

from apps.app_server.models.base.base_model import BaseModel


class ReviewSession(BaseModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='review_sessions',
    )
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'review_sessions'
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['user', 'started_at'], name='idx_review_session_user_start'),
        ]

    def __str__(self):
        return f'Session by {self.user.email} at {self.started_at}'
