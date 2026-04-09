from rest_framework import serializers

from apps.app_server.serializers.base_serializer import CoreModelSerializer
from apps.app_server.models.lesson_model import (
    Lesson,
    LESSON_TYPE_LESSON,
    LESSON_TYPE_QUIZ,
)


class LessonSerializer(CoreModelSerializer):
    status = serializers.SerializerMethodField()

    def get_status(self, obj):
        status_map = self.context.get('lesson_status_map', {})
        return status_map.get(obj.id)

    def validate(self, attrs):
        instance = getattr(self, 'instance', None)

        lesson_type = attrs.get('lesson_type', getattr(instance, 'lesson_type', LESSON_TYPE_LESSON))
        video_url = attrs.get('video_url', getattr(instance, 'video_url', ''))
        video_file = attrs.get('video_file', getattr(instance, 'video_file', None))
        content_markdown = attrs.get('content_markdown', getattr(instance, 'content_markdown', ''))
        quiz_questions = attrs.get('quiz_questions', getattr(instance, 'quiz_questions', []))
        is_final = attrs.get('is_final', getattr(instance, 'is_final', False))
        module = attrs.get('module', getattr(instance, 'module', None))
        is_create = instance is None

        if lesson_type == LESSON_TYPE_LESSON:
            should_validate_video = is_create or any(
                field in attrs for field in ('lesson_type', 'video_url', 'video_file')
            )
            should_validate_summary = is_create or any(
                field in attrs for field in ('lesson_type', 'content_markdown')
            )
            if should_validate_video and not (str(video_url or '').strip() or video_file):
                raise serializers.ValidationError({'video_url': ['Video source is required (video_url or video_file).']})
            if should_validate_summary and not str(content_markdown or '').strip():
                raise serializers.ValidationError({'content_markdown': ['Summary text is required for lessons.']})
            if quiz_questions:
                raise serializers.ValidationError({'quiz_questions': ['Quiz questions are only supported for quiz lessons.']})
            if is_final:
                raise serializers.ValidationError({'is_final': ['Final lesson must be quiz type.']})
            return attrs

        if lesson_type == LESSON_TYPE_QUIZ:
            if video_file:
                raise serializers.ValidationError({'video_file': ['Video file is not allowed for quiz lessons.']})
            self._validate_quiz_questions(quiz_questions)
            if is_final and module:
                queryset = Lesson.objects.filter(module=module, is_final=True)
                if instance:
                    queryset = queryset.exclude(id=instance.id)
                if queryset.exists():
                    raise serializers.ValidationError({'is_final': ['This module already has a final quiz lesson.']})
            return attrs

        raise serializers.ValidationError({'lesson_type': ['Unsupported lesson type.']})

    def _validate_quiz_questions(self, quiz_questions):
        if not isinstance(quiz_questions, list) or not quiz_questions:
            raise serializers.ValidationError({'quiz_questions': ['Quiz questions are required for quiz lessons.']})

        for index, item in enumerate(quiz_questions):
            if not isinstance(item, dict):
                raise serializers.ValidationError({'quiz_questions': [f'Question #{index + 1} must be an object.']})

            question = item.get('question')
            options = item.get('options')
            correct_index = item.get('correct_index')

            if not isinstance(question, str) or not question.strip():
                raise serializers.ValidationError({'quiz_questions': [f'Question #{index + 1} must have text.']})
            if not isinstance(options, list) or len(options) != 4:
                raise serializers.ValidationError({'quiz_questions': [f'Question #{index + 1} must have exactly 4 options.']})
            if any(not isinstance(option, str) or not option.strip() for option in options):
                raise serializers.ValidationError({'quiz_questions': [f'Question #{index + 1} has invalid option text.']})
            if not isinstance(correct_index, int) or correct_index < 0 or correct_index > 3:
                raise serializers.ValidationError({'quiz_questions': [f'Question #{index + 1} has invalid correct index.']})

    class Meta:
        model = Lesson
        fields = [
            'id', 'module', 'title', 'lesson_type', 'video_url',
            'video_file', 'transcript_text', 'transcript_status', 'transcript_error', 'transcript_language',
            'content_markdown', 'quiz_questions', 'is_final',
            'min_watch_time', 'order_index', 'status', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'transcript_text', 'transcript_status', 'transcript_error']
        extra_kwargs = {
            'video_file': {'write_only': True, 'required': False},
        }
