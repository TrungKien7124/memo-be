from rest_framework import serializers

from apps.les.services.lesson_ingestion_status_service import LESSON_PIPELINE_STATUS_BATCH_MAX_IDS


class LessonIngestionLessonStatusBatchRequestSerializer(serializers.Serializer):
    lesson_ids = serializers.ListField(
        child=serializers.UUIDField(),
        allow_empty=False,
        min_length=1,
        max_length=LESSON_PIPELINE_STATUS_BATCH_MAX_IDS,
    )

    def validate_lesson_ids(self, value):
        seen = set()
        ordered_unique = []
        for lesson_id in value:
            if lesson_id in seen:
                continue
            seen.add(lesson_id)
            ordered_unique.append(lesson_id)
        return ordered_unique


class LessonIngestionJobLatestSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    job_type = serializers.CharField()
    trigger_source = serializers.CharField()
    status = serializers.CharField()
    source_version = serializers.CharField()
    started_at = serializers.DateTimeField(allow_null=True)
    finished_at = serializers.DateTimeField(allow_null=True)
    created_at = serializers.DateTimeField()


class LessonIngestionJobFailedLatestSerializer(LessonIngestionJobLatestSerializer):
    error_message = serializers.CharField(allow_blank=True)
    error_payload = serializers.JSONField()


class LessonIngestionLessonStatusSerializer(serializers.Serializer):
    lesson_id = serializers.UUIDField()
    supported_for_ingestion = serializers.BooleanField()
    lesson_type = serializers.CharField()

    publication_status = serializers.CharField()
    is_active = serializers.BooleanField()
    publication_error = serializers.CharField(allow_blank=True)
    transcript_status = serializers.CharField()
    transcript_error = serializers.CharField(allow_blank=True)

    latest_job = LessonIngestionJobLatestSerializer(allow_null=True)
    latest_completed_job_id = serializers.UUIDField(allow_null=True)
    latest_failed_job = LessonIngestionJobFailedLatestSerializer(allow_null=True)

    active_chunk_count = serializers.IntegerField()
    has_active_chunk_set = serializers.BooleanField()

    active_chunk_set_isolation_ready = serializers.BooleanField()
    active_chunk_set_embedding_model_matches = serializers.BooleanField()

    last_indexed_at = serializers.DateTimeField(allow_null=True)

