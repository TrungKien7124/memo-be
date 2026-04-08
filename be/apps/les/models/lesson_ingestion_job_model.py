from django.db import models

from apps.app_server.models.base_model import BaseModel


class LessonIngestionJobType(models.TextChoices):
    """Danh sách loại job ingestion hỗ trợ trong lesson RAG pipeline."""

    INGEST = 'ingest', 'Ingest'
    REINGEST = 'reingest', 'Reingest'
    DELETE_INDEX = 'delete_index', 'Delete Index'


class LessonIngestionJobStatus(models.TextChoices):
    """Danh sách trạng thái runtime của một ingestion job."""

    PENDING = 'pending', 'Pending'
    PROCESSING = 'processing', 'Processing'
    COMPLETED = 'completed', 'Completed'
    FAILED = 'failed', 'Failed'
    CANCELLED = 'cancelled', 'Cancelled'


class LessonIngestionTriggerSource(models.TextChoices):
    """Nguồn sự kiện tạo ra ingestion job."""

    LESSON_CREATED = 'lesson_created', 'Lesson Created'
    LESSON_UPDATED = 'lesson_updated', 'Lesson Updated'
    MANUAL_REINDEX = 'manual_reindex', 'Manual Reindex'
    LESSON_DELETED = 'lesson_deleted', 'Lesson Deleted'


class LessonIngestionJob(BaseModel):
    """
    Lưu một lần chạy ingestion cho lesson để phục vụ audit và retry.

    Mục đích:
        Theo dõi vòng đời của mỗi lần ingest/reingest/delete-index, bao gồm
        trạng thái, thời gian chạy và payload lỗi nếu có.
    """

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
        """
        Trả về chuỗi mô tả ngắn của ingestion job.

        Returns:
            Chuỗi chứa lesson title, job type và status hiện tại.

        Raises:
            Không chủ động raise exception.
        """
        return f'{self.lesson.title} [{self.job_type}:{self.status}]'
