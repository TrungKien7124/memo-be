from django.conf import settings
from django.db import models

from apps.app_server.models.base.base_model import BaseModel


class UserXP(BaseModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='xp_summary',
    )
    total_xp = models.PositiveIntegerField(default=0)
    weekly_xp = models.PositiveIntegerField(default=0)
    monthly_xp = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'user_xp'
        ordering = ['-total_xp']

    def __str__(self):
        return f'{self.user.email}: {self.total_xp} XP'
