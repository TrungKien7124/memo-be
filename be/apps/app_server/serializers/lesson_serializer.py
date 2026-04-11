from django.conf import settings
from rest_framework import serializers

from apps.app_server.serializers.base_serializer import CoreModelSerializer
from apps.app_server.models.lesson_model import (
    Lesson,
    LESSON_TYPE_LESSON,
    LESSON_TYPE_QUIZ,
)


class LessonSerializer(CoreModelSerializer):
    status = serializers.SerializerMethodField()
    transcript_file = serializers.FileField(write_only=True, required=False, allow_null=True)
    MAX_TRANSCRIPT_FILE_BYTES = 2 * 1024 * 1024

    def get_status(self, obj):
        status_map = self.context.get('lesson_status_map', {})
        return status_map.get(obj.id)

    def validate(self, attrs):
        instance = getattr(self, 'instance', None)

        lesson_type = attrs.get('lesson_type', getattr(instance, 'lesson_type', LESSON_TYPE_LESSON))
        video_url = attrs.get('video_url', getattr(instance, 'video_url', ''))
        video_file = attrs.get('video_file', getattr(instance, 'video_file', None))
        transcript_file = attrs.get('transcript_file')
        content_markdown = attrs.get('content_markdown', getattr(instance, 'content_markdown', ''))
        is_final = attrs.get('is_final', getattr(instance, 'is_final', False))
        module = attrs.get('module', getattr(instance, 'module', None))
        is_create = instance is None
        auto_transcribe_enabled = getattr(settings, 'LESSON_AUTO_TRANSCRIBE_ENABLED', False)

        transcript_text_provided = 'transcript_text' in attrs
        transcript_text_value = attrs.get('transcript_text', '')
        transcript_text_normalized = str(transcript_text_value or '').strip()
        transcript_file_provided = transcript_file is not None
        transcript_file_normalized = None
        if transcript_file_provided:
            transcript_file_normalized = self._normalize_transcript_file(transcript_file)
        if transcript_file_provided:
            # File input is source of truth when both are provided.
            transcript_text_normalized = transcript_file_normalized
            attrs['transcript_text'] = transcript_file_normalized
        elif transcript_text_provided:
            attrs['transcript_text'] = transcript_text_normalized

        previous_lesson_type = getattr(instance, 'lesson_type', None) if instance is not None else None
        if (
            not is_create
            and previous_lesson_type == LESSON_TYPE_QUIZ
            and lesson_type == LESSON_TYPE_LESSON
        ):
            attrs['quiz_questions'] = []

        if 'quiz_questions' in attrs:
            quiz_questions = attrs['quiz_questions']
        elif instance is not None:
            quiz_questions = getattr(instance, 'quiz_questions', []) or []
        else:
            quiz_questions = []

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
            if video_file and not auto_transcribe_enabled and not transcript_text_normalized:
                raise serializers.ValidationError({
                    'transcript_text': ['Manual transcript is required for uploaded video lessons.'],
                })
            if (
                not is_create
                and not auto_transcribe_enabled
                and 'video_file' in attrs
                and attrs.get('video_file')
            ):
                has_existing_transcript = bool(str(getattr(instance, 'transcript_text', '') or '').strip())
                if not transcript_text_normalized and not has_existing_transcript:
                    raise serializers.ValidationError({
                        'transcript_text': ['Provide transcript_text or transcript_file when replacing video file.'],
                    })
            attrs['_manual_transcript_provided'] = bool(transcript_text_provided or transcript_file_provided)
            attrs['_manual_transcript_value'] = transcript_text_normalized
            return attrs

        if lesson_type == LESSON_TYPE_QUIZ:
            if video_file:
                raise serializers.ValidationError({'video_file': ['Video file is not allowed for quiz lessons.']})
            if transcript_text_provided or transcript_file_provided:
                raise serializers.ValidationError({
                    'transcript_text': ['Transcript fields are only supported for lesson type.'],
                })
            self._validate_quiz_questions(quiz_questions)
            if is_final and module:
                queryset = Lesson.objects.filter(module=module, is_final=True)
                if instance:
                    queryset = queryset.exclude(id=instance.id)
                if queryset.exists():
                    raise serializers.ValidationError({'is_final': ['This module already has a final quiz lesson.']})
            return attrs

        raise serializers.ValidationError({'lesson_type': ['Unsupported lesson type.']})

    def _normalize_transcript_file(self, transcript_file):
        file_name = str(getattr(transcript_file, 'name', '') or '')
        if not file_name.lower().endswith('.txt'):
            raise serializers.ValidationError({'transcript_file': ['Only .txt transcript files are supported.']})
        content_type = getattr(transcript_file, 'content_type', '') or ''
        if content_type and content_type.lower() != 'text/plain':
            raise serializers.ValidationError({'transcript_file': ['Transcript file must be text/plain.']})
        file_size = int(getattr(transcript_file, 'size', 0) or 0)
        if file_size > self.MAX_TRANSCRIPT_FILE_BYTES:
            raise serializers.ValidationError({
                'transcript_file': ['Transcript file is too large (max 2MB).'],
            })
        try:
            raw_bytes = transcript_file.read()
            transcript_file.seek(0)
            normalized = raw_bytes.decode('utf-8').strip()
        except UnicodeDecodeError as exc:
            raise serializers.ValidationError({
                'transcript_file': ['Transcript file must be valid UTF-8 text.'],
            }) from exc
        if not normalized:
            raise serializers.ValidationError({'transcript_file': ['Transcript file is empty.']})
        return normalized

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

    def create(self, validated_data):
        validated_data.pop('transcript_file', None)
        validated_data.pop('_manual_transcript_provided', None)
        validated_data.pop('_manual_transcript_value', None)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data.pop('transcript_file', None)
        validated_data.pop('_manual_transcript_provided', None)
        validated_data.pop('_manual_transcript_value', None)
        return super().update(instance, validated_data)

    class Meta:
        model = Lesson
        fields = [
            'id', 'module', 'title', 'lesson_type', 'video_url',
            'video_file', 'transcript_text', 'transcript_file', 'transcript_status', 'transcript_error', 'transcript_language',
            'content_markdown', 'quiz_questions', 'is_final',
            'min_watch_time', 'order_index', 'status',
            'is_active', 'publication_status', 'publication_error',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'transcript_status', 'transcript_error',
            'is_active', 'publication_status', 'publication_error',
        ]
        extra_kwargs = {
            'video_file': {'write_only': True, 'required': False},
        }
