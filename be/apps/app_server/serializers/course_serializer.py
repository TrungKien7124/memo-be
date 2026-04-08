from rest_framework import serializers

from apps.app_server.serializers.base_serializer import CoreModelSerializer
from apps.app_server.models.course_model import Course


class CourseSerializer(CoreModelSerializer):
    lesson_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Course
        fields = [
            'id', 'title', 'description', 'thumbnail_url',
            'status', 'created_by', 'created_at', 'updated_at', 'lesson_count',
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']
