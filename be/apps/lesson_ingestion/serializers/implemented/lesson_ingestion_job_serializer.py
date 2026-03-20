from rest_framework import serializers

from apps.lesson_ingestion.models import LessonIngestionJob


class LessonIngestionJobListSerializer(serializers.ModelSerializer):
    lesson_id = serializers.UUIDField(source='lesson.id', read_only=True)

    class Meta:
        model = LessonIngestionJob
        fields = (
            'id',
            'lesson_id',
            'job_type',
            'trigger_source',
            'status',
            'source_version',
            'started_at',
            'finished_at',
            'created_at',
            'updated_at',
        )


class LessonIngestionJobDetailSerializer(LessonIngestionJobListSerializer):
    error_message = serializers.CharField()
    error_payload = serializers.JSONField()

    class Meta:
        model = LessonIngestionJob
        fields = (
            'id',
            'lesson_id',
            'job_type',
            'trigger_source',
            'status',
            'source_version',
            'started_at',
            'finished_at',
            'created_at',
            'updated_at',
            'error_message',
            'error_payload',
        )

