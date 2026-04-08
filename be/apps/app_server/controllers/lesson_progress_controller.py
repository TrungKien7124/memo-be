from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from apps.app_server.controllers.base_controller import CoreModelViewSet
from apps.app_server.models.lesson_model import LESSON_TYPE_QUIZ
from apps.app_server.models.lesson_progress_model import LessonProgress
from apps.app_server.responses.api_responses import success_response
from apps.app_server.serializers.lesson_progress_serializer import LessonProgressSerializer
from apps.app_server.services.lesson_progress_service import (
    QUIZ_MAX_HEARTS,
    complete_non_quiz_lesson,
    submit_quiz_answer,
)


class LessonProgressViewSet(CoreModelViewSet):
    serializer_class = LessonProgressSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['lesson', 'completed']

    def get_queryset(self):
        return LessonProgress.objects.filter(user=self.request.user).select_related('lesson')

    def _build_response_data(self, progress_instance, quiz_result=None):
        serialized_progress = dict(self.get_serializer(progress_instance).data)
        if quiz_result is not None:
            serialized_progress['quiz_runtime'] = {
                **quiz_result,
                'max_hearts': QUIZ_MAX_HEARTS,
            }
        return serialized_progress

    def create(self, request, *args, **kwargs):
        lesson_id = request.data.get('lesson')
        progress, created = LessonProgress.objects.get_or_create(
            user=request.user,
            lesson_id=lesson_id,
        )
        watched_seconds = int(request.data.get('watched_seconds', 0))
        force_complete = bool(request.data.get('completed', False))
        selected_answer = request.data.get('selected_answer')
        question_index = request.data.get('question_index')

        if progress.lesson.lesson_type == LESSON_TYPE_QUIZ:
            selected_answer_value = selected_answer if isinstance(selected_answer, int) else None
            question_index_value = question_index if isinstance(question_index, int) else None
            quiz_result = submit_quiz_answer(
                progress,
                selected_answer=selected_answer_value,
                question_index=question_index_value,
            )
        else:
            complete_non_quiz_lesson(progress, watched_seconds=watched_seconds, force_complete=force_complete)
            quiz_result = None

        payload = self._build_response_data(progress, quiz_result=quiz_result)
        return success_response(
            data=payload,
            message='Lưu tiến độ bài học thành công.',
            http_status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        watched_seconds = int(request.data.get('watched_seconds', 0))
        force_complete = bool(request.data.get('completed', False))
        selected_answer = request.data.get('selected_answer')
        question_index = request.data.get('question_index')

        if instance.lesson.lesson_type == LESSON_TYPE_QUIZ:
            selected_answer_value = selected_answer if isinstance(selected_answer, int) else None
            question_index_value = question_index if isinstance(question_index, int) else None
            quiz_result = submit_quiz_answer(
                instance,
                selected_answer=selected_answer_value,
                question_index=question_index_value,
            )
        else:
            complete_non_quiz_lesson(instance, watched_seconds=watched_seconds, force_complete=force_complete)
            quiz_result = None

        payload = self._build_response_data(instance, quiz_result=quiz_result)
        return success_response(
            data=payload,
            message='Cập nhật tiến độ bài học thành công.',
        )
