from django.db import models

from apps.app_server.models.base.base_model import BaseModel


class LessonSourceDocumentType(models.TextChoices):
    TEXT_MARKDOWN = 'text_markdown', 'Text Markdown'
    VIDEO_URL_TRANSCRIPT = 'video_url_transcript', 'Video URL Transcript'


class LessonSourceDocument(BaseModel):
    lesson = models.ForeignKey(
        'app_server.Lesson',
        on_delete=models.CASCADE,
        related_name='source_documents',
    )
    ingestion_job = models.ForeignKey(
        'lesson_ingestion.LessonIngestionJob',
        on_delete=models.CASCADE,
        related_name='source_documents',
    )
    source_type = models.CharField(max_length=32, choices=LessonSourceDocumentType.choices)
    source_locator = models.CharField(max_length=500, blank=True, default='')
    raw_text = models.TextField(blank=True, default='')
    normalized_text = models.TextField(blank=True, default='')
    language_code = models.CharField(max_length=16, blank=True, default='')
    checksum = models.CharField(max_length=128, blank=True, default='')
    metadata_json = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'lesson_source_documents'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['lesson', 'source_type'], name='idx_source_doc_lesson_type'),
            models.Index(fields=['checksum'], name='idx_source_doc_checksum'),
        ]

    def __str__(self):
        return f'{self.lesson.title} [{self.source_type}]'
