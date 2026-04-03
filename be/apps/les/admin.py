from django.contrib import admin

from apps.les.models import (
    LessonContentChunk,
    LessonIngestionJob,
    LessonSourceDocument,
)


@admin.register(LessonIngestionJob)
class LessonIngestionJobAdmin(admin.ModelAdmin):
    list_display = ('lesson', 'job_type', 'status', 'trigger_source', 'created_at', 'finished_at')
    list_filter = ('job_type', 'status', 'trigger_source')
    search_fields = ('lesson__title', 'lesson__id', 'error_message')
    readonly_fields = ('created_at', 'updated_at', 'started_at', 'finished_at')


@admin.register(LessonSourceDocument)
class LessonSourceDocumentAdmin(admin.ModelAdmin):
    list_display = ('lesson', 'source_type', 'language_code', 'checksum', 'created_at')
    list_filter = ('source_type', 'language_code')
    search_fields = ('lesson__title', 'source_locator', 'checksum')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(LessonContentChunk)
class LessonContentChunkAdmin(admin.ModelAdmin):
    list_display = ('lesson', 'chunk_index', 'is_active', 'embedding_provider', 'created_at')
    list_filter = ('is_active', 'embedding_provider')
    search_fields = ('lesson__title', 'vector_document_id', 'content')
    readonly_fields = ('created_at', 'updated_at')
