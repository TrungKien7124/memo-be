from django.db import models

from apps.app_server.models.base.base_model import BaseModel


class Lesson(BaseModel):
    module = models.ForeignKey(
        'app_server.Module',
        on_delete=models.CASCADE,
        related_name='lessons',
    )
    title = models.CharField(max_length=255)
    video_url = models.URLField(max_length=500)
    min_watch_time = models.PositiveIntegerField(default=120, help_text='Minimum seconds to mark complete')
    order_index = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'lessons'
        ordering = ['order_index']

    def __str__(self):
        return self.title
