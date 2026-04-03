from django.db import models

from apps.app_server.models.base.base_model import BaseModel


class LessonContentChunk(BaseModel):
    """
    Lưu từng chunk nội dung đã được tách ra từ source document của lesson.

    Mục đích:
        Liên kết chunk text trong relational database với document tương ứng
        trong vector store để retrieval, cleanup và audit dễ theo dõi.
    """

    lesson = models.ForeignKey(
        'app_server.Lesson',
        on_delete=models.CASCADE,
        related_name='content_chunks',
    )
    ingestion_job = models.ForeignKey(
        'lesson_ingestion.LessonIngestionJob',
        on_delete=models.CASCADE,
        related_name='content_chunks',
    )
    source_document = models.ForeignKey(
        'lesson_ingestion.LessonSourceDocument',
        on_delete=models.CASCADE,
        related_name='content_chunks',
    )
    chunk_index = models.PositiveIntegerField()
    content = models.TextField()
    token_estimate = models.PositiveIntegerField(default=0)
    char_start = models.PositiveIntegerField(default=0)
    char_end = models.PositiveIntegerField(default=0)
    vector_document_id = models.CharField(max_length=255, blank=True, default='')
    embedding_provider = models.CharField(max_length=100, blank=True, default='')
    embedding_model = models.CharField(max_length=255, blank=True, default='')
    metadata_json = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=False, db_index=True)

    class Meta:
        db_table = 'lesson_content_chunks'
        ordering = ['chunk_index', 'created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['source_document', 'chunk_index'],
                name='uniq_chunk_source_index',
            ),
        ]
        indexes = [
            models.Index(fields=['lesson', 'is_active'], name='idx_chunk_lesson_active'),
            models.Index(fields=['vector_document_id'], name='idx_chunk_vector_doc'),
        ]

    def __str__(self):
        """
        Trả về chuỗi mô tả ngắn của chunk.

        Returns:
            Chuỗi gồm lesson title và chunk index.

        Raises:
            Không chủ động raise exception.
        """
        return f'{self.lesson.title} chunk {self.chunk_index}'
