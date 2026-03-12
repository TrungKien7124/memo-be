from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.app_server.controllers.base.base_controller import CoreModelViewSet
from apps.app_server.models.implemented.lms_lesson_progress_model import LessonProgress
from apps.app_server.serializers.implemented.lms_lesson_progress_serializer import LessonProgressSerializer
from apps.app_server.services.lms_progress_service import update_lesson_progress


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
        update_lesson_progress(progress, watched_seconds)
        serializer = self.get_serializer(progress)
        return Response(
            {'data': serializer.data},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        watched_seconds = int(request.data.get('watched_seconds', 0))
        update_lesson_progress(instance, watched_seconds)
        serializer = self.get_serializer(instance)
        return Response({'data': serializer.data})
