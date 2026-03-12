from apps.app_server.serializers.base.base_serializer import CoreModelSerializer
from apps.app_server.models.implemented.cms_course_model import Course


class CourseSerializer(CoreModelSerializer):
    class Meta:
        model = Course
        fields = [
            'id', 'title', 'description', 'thumbnail_url',
            'status', 'created_by', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']
