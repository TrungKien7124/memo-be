from django.db import models

from apps.app_server.models.base_model import BaseModel

ROLE_USER = 'user'
ROLE_ASSISTANT = 'assistant'
ROLE_SYSTEM = 'system'

ROLE_CHOICES = [
    (ROLE_USER, 'User'),
    (ROLE_ASSISTANT, 'Assistant'),
    (ROLE_SYSTEM, 'System'),
]


class Message(BaseModel):
    conversation = models.ForeignKey(
        'ai.Conversation',
        on_delete=models.CASCADE,
        related_name='messages',
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()

    class Meta:
        db_table = 'messages'
        ordering = ['created_at']

    def __str__(self):
        return f'[{self.role}] {self.content[:50]}'
