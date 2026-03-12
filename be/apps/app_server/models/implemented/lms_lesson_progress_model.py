from django.conf import settings
from django.db import models

from apps.app_server.models.base.base_model import BaseModel


class LessonProgress(BaseModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='lesson_progress',
    )
    lesson = models.ForeignKey(
        'app_server.Lesson',
        on_delete=models.CASCADE,
        related_name='progress_records',
    )
    watched_seconds = models.PositiveIntegerField(default=0)
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'lesson_progress'
        ordering = ['-updated_at']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'lesson'],
                name='unique_user_lesson_progress',
            )
        ]
        indexes = [
            models.Index(fields=['user'], name='idx_lesson_progress_user'),
        ]

    def __str__(self):
        return f'{self.user.email} - {self.lesson.title}'
