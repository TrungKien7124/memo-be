from rest_framework.permissions import IsAuthenticated

from apps.app_server.controllers.base.base_controller import CoreModelViewSet
from apps.app_server.models.implemented.cms_lesson_model import Lesson
from apps.app_server.serializers.implemented.cms_lesson_serializer import LessonSerializer
from apps.app_server.permissions.role_permission import IsTeacherOrAdmin
from apps.app_server.services.lms_unlock_service import get_lesson_status_map


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
