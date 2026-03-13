from apps.app_server.serializers.base.base_serializer import CoreModelSerializer
from apps.app_server.models.implemented.lms_lesson_progress_model import LessonProgress


class LessonProgressSerializer(CoreModelSerializer):
    class Meta:
        model = LessonProgress
        fields = [
            'id', 'user', 'lesson', 'watched_seconds',
            'quiz_score', 'quiz_total_questions', 'quiz_passed', 'quiz_attempts',
            'completed', 'completed_at', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'user', 'completed', 'completed_at', 'created_at', 'updated_at',
            'quiz_score', 'quiz_total_questions', 'quiz_passed', 'quiz_attempts',
        ]
