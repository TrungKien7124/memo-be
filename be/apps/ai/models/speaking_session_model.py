from django.conf import settings
from django.db import models

from apps.app_server.models.base_model import BaseModel


class SpeakingSession(BaseModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='speaking_sessions',
    )
    topic_template = models.CharField(max_length=255, blank=True, default='')
    conversation = models.OneToOneField(
        'ai.Conversation',
        on_delete=models.CASCADE,
        related_name='speaking_session',
        null=True, blank=True,
    )
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'speaking_sessions'
        ordering = ['-started_at']

    def __str__(self):
        return f'Speaking: {self.user.email} - {self.topic_template}'
