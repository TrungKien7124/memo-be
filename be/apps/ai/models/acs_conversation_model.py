from django.conf import settings
from django.db import models

from apps.app_server.models.base.base_model import BaseModel


class Conversation(BaseModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='conversations',
    )
    topic = models.CharField(max_length=255, blank=True, default='')
    lesson = models.ForeignKey(
        'app_server.Lesson',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ai_conversations',
    )

    class Meta:
        db_table = 'conversations'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.email} - {self.topic or "Free chat"}'
