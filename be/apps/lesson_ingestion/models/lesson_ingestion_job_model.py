from django.db import models

from apps.app_server.models.base.base_model import BaseModel


class LessonIngestionJobType(models.TextChoices):
    INGEST = 'ingest', 'Ingest'
    REINGEST = 'reingest', 'Reingest'
    DELETE_INDEX = 'delete_index', 'Delete Index'


class LessonIngestionJobStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    PROCESSING = 'processing', 'Processing'
    COMPLETED = 'completed', 'Completed'
    FAILED = 'failed', 'Failed'
    CANCELLED = 'cancelled', 'Cancelled'


class LessonIngestionTriggerSource(models.TextChoices):
    LESSON_CREATED = 'lesson_created', 'Lesson Created'
    LESSON_UPDATED = 'lesson_updated', 'Lesson Updated'
    MANUAL_REINDEX = 'manual_reindex', 'Manual Reindex'
    LESSON_DELETED = 'lesson_deleted', 'Lesson Deleted'


class LessonIngestionJob(BaseModel):
    lesson = models.ForeignKey(
        'app_server.Lesson',
        on_delete=models.CASCADE,
        related_name='ingestion_jobs',
    )
    job_type = models.CharField(max_length=20, choices=LessonIngestionJobType.choices)
    status = models.CharField(
        max_length=20,
        choices=LessonIngestionJobStatus.choices,
        default=LessonIngestionJobStatus.PENDING,
    )
    trigger_source = models.CharField(max_length=20, choices=LessonIngestionTriggerSource.choices)
    source_version = models.CharField(max_length=64, blank=True, default='')
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True, default='')
    error_payload = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'lesson_ingestion_jobs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['lesson', 'status'], name='idx_ingest_job_lesson_status'),
            models.Index(fields=['status', 'created_at'], name='idx_ingest_job_status_created'),
        ]

    def __str__(self):
        return f'{self.lesson.title} [{self.job_type}:{self.status}]'
