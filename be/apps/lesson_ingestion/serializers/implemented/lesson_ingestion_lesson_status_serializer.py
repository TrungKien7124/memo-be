from rest_framework import serializers


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

    latest_job = LessonIngestionJobLatestSerializer(allow_null=True)
    latest_completed_job_id = serializers.UUIDField(allow_null=True)
    latest_failed_job = LessonIngestionJobFailedLatestSerializer(allow_null=True)

    active_chunk_count = serializers.IntegerField()
    has_active_chunk_set = serializers.BooleanField()

    last_indexed_at = serializers.DateTimeField(allow_null=True)

