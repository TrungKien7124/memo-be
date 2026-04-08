from django.conf import settings
from django.db import models

from apps.app_server.models.base_model import BaseModel

CARD_TYPE_VOCABULARY = 'vocabulary'
CARD_TYPE_PHRASE = 'phrase'
CARD_TYPE_SENTENCE = 'sentence'

CARD_TYPE_CHOICES = [
    (CARD_TYPE_VOCABULARY, 'Vocabulary'),
    (CARD_TYPE_PHRASE, 'Phrase'),
    (CARD_TYPE_SENTENCE, 'Sentence'),
]


class Flashcard(BaseModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='flashcards',
    )
    folder = models.ForeignKey(
        'app_server.Folder',
        on_delete=models.CASCADE,
        related_name='flashcards',
    )
    front_text = models.TextField()
    back_text = models.TextField()
    ipa = models.CharField(max_length=255, blank=True, default='')
    audio_url = models.URLField(max_length=500, blank=True, default='')
    image_url = models.URLField(max_length=500, blank=True, default='')
    card_type = models.CharField(max_length=20, choices=CARD_TYPE_CHOICES, default=CARD_TYPE_VOCABULARY)

    class Meta:
        db_table = 'flashcards'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'folder'], name='idx_flashcard_user_folder'),
        ]

    def __str__(self):
        return self.front_text[:50]
