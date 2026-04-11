from django.db import models
from django.db.models import Q

from apps.app_server.models.base_model import BaseModel

LESSON_TYPE_LESSON = 'lesson'
LESSON_TYPE_QUIZ = 'quiz'
# Backward-compatible aliases for internal imports/tests.
LESSON_TYPE_VIDEO = LESSON_TYPE_LESSON
LESSON_TYPE_TEXT = LESSON_TYPE_LESSON

LESSON_TYPE_CHOICES = [
    (LESSON_TYPE_LESSON, 'Lesson'),
    (LESSON_TYPE_QUIZ, 'Quiz'),
]
TRANSCRIPT_STATUS_NOT_STARTED = 'not_started'
TRANSCRIPT_STATUS_PROCESSING = 'processing'
TRANSCRIPT_STATUS_READY = 'ready'
TRANSCRIPT_STATUS_FAILED = 'failed'
TRANSCRIPT_STATUS_CHOICES = [
    (TRANSCRIPT_STATUS_NOT_STARTED, 'Not started'),
    (TRANSCRIPT_STATUS_PROCESSING, 'Processing'),
    (TRANSCRIPT_STATUS_READY, 'Ready'),
    (TRANSCRIPT_STATUS_FAILED, 'Failed'),
]

PUBLICATION_STATUS_DRAFT = 'draft'
PUBLICATION_STATUS_PROCESSING = 'processing'
PUBLICATION_STATUS_READY = 'ready'
PUBLICATION_STATUS_FAILED = 'failed'
PUBLICATION_STATUS_CHOICES = [
    (PUBLICATION_STATUS_DRAFT, 'Draft'),
    (PUBLICATION_STATUS_PROCESSING, 'Processing'),
    (PUBLICATION_STATUS_READY, 'Ready'),
    (PUBLICATION_STATUS_FAILED, 'Failed'),
]


class Lesson(BaseModel):
    module = models.ForeignKey(
        'app_server.Module',
        on_delete=models.CASCADE,
        related_name='lessons',
    )
    title = models.CharField(max_length=255)
    lesson_type = models.CharField(max_length=10, choices=LESSON_TYPE_CHOICES, default=LESSON_TYPE_LESSON)
    video_url = models.URLField(max_length=500, blank=True, default='')
    video_file = models.FileField(upload_to='lessons/videos/', blank=True, null=True)
    content_markdown = models.TextField(blank=True, default='')
    transcript_text = models.TextField(blank=True, default='')
    transcript_status = models.CharField(
        max_length=20,
        choices=TRANSCRIPT_STATUS_CHOICES,
        default=TRANSCRIPT_STATUS_NOT_STARTED,
    )
    transcript_error = models.TextField(blank=True, default='')
    transcript_language = models.CharField(max_length=12, blank=True, default='en')
    quiz_questions = models.JSONField(default=list, blank=True)
    is_final = models.BooleanField(default=False)
    min_watch_time = models.PositiveIntegerField(default=120, help_text='Minimum seconds to mark complete')
    order_index = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(
        default=True,
        help_text='When false, learners do not see this lesson until publication pipeline completes.',
    )
    publication_status = models.CharField(
        max_length=20,
        choices=PUBLICATION_STATUS_CHOICES,
        default=PUBLICATION_STATUS_READY,
    )
    publication_error = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'lessons'
        ordering = ['order_index', 'title', 'created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['module'],
                condition=Q(is_final=True),
                name='unique_final_lesson_per_module',
            ),
        ]

    def __str__(self):
        return self.title
