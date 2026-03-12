from rest_framework.permissions import IsAuthenticated

from apps.app_server.controllers.base.base_controller import CoreModelViewSet
from apps.app_server.models.implemented.cms_lesson_model import Lesson
from apps.app_server.serializers.implemented.cms_lesson_serializer import LessonSerializer
from apps.app_server.permissions.role_permission import IsTeacherOrAdmin


class LessonViewSet(CoreModelViewSet):
    serializer_class = LessonSerializer
    filterset_fields = ['module']

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsAuthenticated(), IsTeacherOrAdmin()]
        return [IsAuthenticated()]

    def get_queryset(self):
        return Lesson.objects.select_related('module').all()
