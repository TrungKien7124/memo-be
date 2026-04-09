from django.db import models
from django.core.exceptions import ValidationError

from apps.app_server.models.base_model import BaseModel


class LessonComment(BaseModel):
    lesson = models.ForeignKey(
        'app_server.Lesson',
        on_delete=models.CASCADE,
        related_name='comments',
    )
    user = models.ForeignKey(
        'app_server.User',
        on_delete=models.CASCADE,
        related_name='lesson_comments',
    )
    parent = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='replies',
    )
    content = models.TextField()
    edited_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'lesson_comments'
        ordering = ['created_at']

    def clean(self):
        if self.parent_id and self.lesson_id and self.parent.lesson_id != self.lesson_id:
            raise ValidationError({'parent': 'Parent comment must belong to the same lesson.'})
        if not self.is_deleted and not str(self.content or '').strip():
            raise ValidationError({'content': 'Comment content must not be blank.'})

    def save(self, *args, **kwargs):
        if self.is_deleted:
            self.full_clean(exclude=['content'])
        else:
            self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'LessonComment({self.id})'
