from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.app_server.models.base.app_server_base_model import AppServerBaseModel


from apps.app_server.models.implemented.nfs_folder_model import Folder


class Flashcard(AppServerBaseModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="flashcards",
        db_column="user_id",
    )
    folder = models.ForeignKey(
        Folder,
        on_delete=models.CASCADE,
        related_name="flashcards",
        db_column="folder_id",
    )
    front_text = models.TextField()
    back_text = models.TextField()
    ipa = models.CharField(max_length=255, blank=True, null=True)
    audio_url = models.TextField(blank=True, null=True)
    image_url = models.TextField(blank=True, null=True)
    card_type = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "flashcards"

    def __str__(self) -> str:
        return self.front_text
