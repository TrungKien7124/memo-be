from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.app_server.controllers.base.base_controller import CoreModelViewSet
from apps.app_server.models.implemented.cms_lesson_model import LESSON_TYPE_QUIZ
from apps.app_server.models.implemented.lms_lesson_progress_model import LessonProgress
from apps.app_server.serializers.implemented.lms_lesson_progress_serializer import LessonProgressSerializer
from apps.app_server.services.lms_progress_service import (
    QUIZ_PASS_THRESHOLD_PERCENT,
    complete_non_quiz_lesson,
    submit_quiz_lesson,
)


class LessonProgressViewSet(CoreModelViewSet):
    serializer_class = LessonProgressSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['lesson', 'completed']

    def get_queryset(self):
        return LessonProgress.objects.filter(user=self.request.user).select_related('lesson')

    def create(self, request, *args, **kwargs):
        lesson_id = request.data.get('lesson')
        progress, created = LessonProgress.objects.get_or_create(
            user=request.user,
            lesson_id=lesson_id,
        )
        watched_seconds = int(request.data.get('watched_seconds', 0))
        force_complete = bool(request.data.get('completed', False))
        selected_answers = request.data.get('selected_answers', [])

        if progress.lesson.lesson_type == LESSON_TYPE_QUIZ:
            quiz_result = submit_quiz_lesson(progress, selected_answers)
        else:
            complete_non_quiz_lesson(progress, watched_seconds=watched_seconds, force_complete=force_complete)
            quiz_result = None

        serializer = self.get_serializer(progress)
        payload = {'data': serializer.data}
        if quiz_result is not None:
            payload['quiz_result'] = {
                **quiz_result,
                'pass_threshold_percent': QUIZ_PASS_THRESHOLD_PERCENT,
            }
        return Response(
            payload,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        watched_seconds = int(request.data.get('watched_seconds', 0))
        force_complete = bool(request.data.get('completed', False))
        selected_answers = request.data.get('selected_answers', [])

        if instance.lesson.lesson_type == LESSON_TYPE_QUIZ:
            quiz_result = submit_quiz_lesson(instance, selected_answers)
        else:
            complete_non_quiz_lesson(instance, watched_seconds=watched_seconds, force_complete=force_complete)
            quiz_result = None

        serializer = self.get_serializer(instance)
        payload = {'data': serializer.data}
        if quiz_result is not None:
            payload['quiz_result'] = {
                **quiz_result,
                'pass_threshold_percent': QUIZ_PASS_THRESHOLD_PERCENT,
            }
        return Response(payload)
