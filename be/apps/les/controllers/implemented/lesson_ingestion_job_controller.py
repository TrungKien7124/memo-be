from rest_framework.permissions import IsAuthenticated

from apps.app_server.controllers.base.base_controller import CoreModelViewSet
from apps.app_server.permissions.role_permission import IsTeacherOrAdmin
from apps.les.models import LessonIngestionJob
from apps.les.serializers.implemented.lesson_ingestion_job_serializer import (
    LessonIngestionJobDetailSerializer,
    LessonIngestionJobListSerializer,
)


class LessonIngestionJobViewSet(CoreModelViewSet):
    queryset = LessonIngestionJob.objects.select_related('lesson').all()
    serializer_class = LessonIngestionJobListSerializer
    http_method_names = ['get']

    def get_permissions(self):
        return [IsAuthenticated(), IsTeacherOrAdmin()]

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return LessonIngestionJobDetailSerializer
        return LessonIngestionJobListSerializer

