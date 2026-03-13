from django.db import models
from django.db.models import Q

from apps.app_server.models.base.base_model import BaseModel

LESSON_TYPE_VIDEO = 'video'
LESSON_TYPE_TEXT = 'text'
LESSON_TYPE_QUIZ = 'quiz'

LESSON_TYPE_CHOICES = [
    (LESSON_TYPE_VIDEO, 'Video'),
    (LESSON_TYPE_TEXT, 'Text'),
    (LESSON_TYPE_QUIZ, 'Quiz'),
]


class Lesson(BaseModel):
    module = models.ForeignKey(
        'app_server.Module',
        on_delete=models.CASCADE,
        related_name='lessons',
    )
    title = models.CharField(max_length=255)
    lesson_type = models.CharField(max_length=10, choices=LESSON_TYPE_CHOICES, default=LESSON_TYPE_VIDEO)
    video_url = models.URLField(max_length=500, blank=True, default='')
    content_markdown = models.TextField(blank=True, default='')
    quiz_questions = models.JSONField(default=list, blank=True)
    is_final = models.BooleanField(default=False)
    min_watch_time = models.PositiveIntegerField(default=120, help_text='Minimum seconds to mark complete')
    order_index = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'lessons'
        ordering = ['order_index']
        constraints = [
            models.UniqueConstraint(
                fields=['module'],
                condition=Q(is_final=True),
                name='unique_final_lesson_per_module',
            ),
        ]

    def __str__(self):
        return self.title
