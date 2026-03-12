from apps.app_server.serializers.base.base_serializer import CoreModelSerializer
from apps.app_server.models.implemented.cms_lesson_model import Lesson


class LessonSerializer(CoreModelSerializer):
    class Meta:
        model = Lesson
        fields = [
            'id', 'module', 'title', 'video_url',
            'min_watch_time', 'order_index', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
