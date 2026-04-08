from django.conf import settings
from django.db import models

from apps.app_server.models.base_model import BaseModel

COURSE_STATUS_DRAFT = 'draft'
COURSE_STATUS_PUBLISHED = 'published'
COURSE_STATUS_ARCHIVED = 'archived'

COURSE_STATUS_CHOICES = [
    (COURSE_STATUS_DRAFT, 'Draft'),
    (COURSE_STATUS_PUBLISHED, 'Published'),
    (COURSE_STATUS_ARCHIVED, 'Archived'),
]


class Course(BaseModel):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    thumbnail_url = models.URLField(max_length=500, blank=True, default='')
    status = models.CharField(max_length=10, choices=COURSE_STATUS_CHOICES, default=COURSE_STATUS_DRAFT)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='courses_created',
    )

    class Meta:
        db_table = 'courses'
        ordering = ['-created_at']

    def __str__(self):
        return self.title
