from apps.app_server.serializers.base_serializer import CoreModelSerializer
from apps.app_server.models.lesson_progress_model import LessonProgress


class LessonProgressSerializer(CoreModelSerializer):
    class Meta:
        model = LessonProgress
        fields = [
            'id', 'user', 'lesson', 'watched_seconds',
            'quiz_score', 'quiz_total_questions', 'quiz_passed', 'quiz_attempts',
            'quiz_hearts_left', 'quiz_current_question_index', 'quiz_correct_count',
            'completed', 'completed_at', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'user', 'completed', 'completed_at', 'created_at', 'updated_at',
            'quiz_score', 'quiz_total_questions', 'quiz_passed', 'quiz_attempts',
            'quiz_hearts_left', 'quiz_current_question_index', 'quiz_correct_count',
        ]
