from django.conf import settings
from django.db import models

from apps.app_server.models.base_model import BaseModel

XP_SOURCE_LESSON = 'lesson'
XP_SOURCE_REVIEW = 'review'
XP_SOURCE_QUIZ = 'quiz'
XP_SOURCE_SPEAKING = 'speaking'

XP_SOURCE_CHOICES = [
    (XP_SOURCE_LESSON, 'Lesson'),
    (XP_SOURCE_REVIEW, 'Review'),
    (XP_SOURCE_QUIZ, 'Quiz'),
    (XP_SOURCE_SPEAKING, 'Speaking'),
]


class XPTransaction(BaseModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='xp_transactions',
    )
    xp_amount = models.PositiveIntegerField()
    source = models.CharField(max_length=20, choices=XP_SOURCE_CHOICES)
    source_id = models.UUIDField(null=True, blank=True, help_text='ID of the related entity')

    class Meta:
        db_table = 'xp_transactions'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.email} +{self.xp_amount} XP ({self.source})'
