from django.conf import settings
from django.db import models

from apps.app_server.models.base_model import BaseModel


class Folder(BaseModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='folders',
    )
    name = models.CharField(max_length=255)

    class Meta:
        db_table = 'folders'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'name'],
                condition=models.Q(is_deleted=False),
                name='unique_active_folder_name_per_user',
            )
        ]

    def __str__(self):
        return self.name
