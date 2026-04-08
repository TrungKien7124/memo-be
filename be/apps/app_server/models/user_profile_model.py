from django.db import models

from apps.app_server.models.base_model import BaseModel


class UserProfile(BaseModel):
    user = models.OneToOneField(
        'app_server.User',
        on_delete=models.CASCADE,
        related_name='profile',
    )
    display_name = models.CharField(max_length=100, blank=True, default='')
    avatar_url = models.URLField(max_length=500, blank=True, default='')
    timezone = models.CharField(max_length=50, default='UTC')

    class Meta:
        db_table = 'user_profiles'
        ordering = ['-created_at']

    def __str__(self):
        return f'Profile of {self.user.email}'
