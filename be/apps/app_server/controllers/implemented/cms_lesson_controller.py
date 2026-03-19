from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from apps.app_server.controllers.base.base_controller import CoreModelViewSet
from apps.app_server.models.implemented.cms_lesson_model import Lesson
from apps.app_server.serializers.implemented.cms_lesson_serializer import LessonSerializer
from apps.app_server.permissions.role_permission import IsTeacherOrAdmin
from apps.app_server.services.lms_unlock_service import get_lesson_status_map
from apps.lesson_ingestion.models import LessonIngestionTriggerSource
from apps.lesson_ingestion.services.lesson_ingestion_scheduling_service import (
    extract_ingestion_relevant_fields,
    schedule_lesson_index_delete,
    schedule_lesson_ingestion,
    schedule_lesson_reingestion_if_needed,
)


class LessonViewSet(CoreModelViewSet):
    serializer_class = LessonSerializer
    filterset_fields = ['module']

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsAuthenticated(), IsTeacherOrAdmin()]
        return [IsAuthenticated()]

    def get_queryset(self):
        return Lesson.objects.select_related('module').all().order_by('order_index', 'created_at')

    def get_serializer_context(self):
        context = super().get_serializer_context()
        user = self.request.user
        module_id = self.request.query_params.get('module')
        if self.action in ('list', 'retrieve') and user.is_authenticated:
            if module_id:
                context['lesson_status_map'] = get_lesson_status_map(user, module_id)
            elif self.action == 'retrieve':
                lesson = self.get_object()
                context['lesson_status_map'] = get_lesson_status_map(user, lesson.module_id)
        return context

    def perform_create(self, serializer):
        super().perform_create(serializer)
        schedule_lesson_ingestion(
            serializer.instance,
            trigger_source=LessonIngestionTriggerSource.LESSON_CREATED,
            job_type=None,
        )

    def perform_update(self, serializer):
        previous_snapshot = extract_ingestion_relevant_fields(serializer.instance)
        super().perform_update(serializer)
        schedule_lesson_reingestion_if_needed(previous_snapshot, serializer.instance)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        schedule_lesson_index_delete(
            instance,
            trigger_source=LessonIngestionTriggerSource.LESSON_DELETED,
        )

        if hasattr(instance, 'soft_delete'):
            instance.soft_delete()
        else:
            self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)
