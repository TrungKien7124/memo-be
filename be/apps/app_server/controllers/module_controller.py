from rest_framework.permissions import IsAuthenticated

from apps.app_server.controllers.base_controller import CoreModelViewSet
from apps.app_server.responses.api_responses import error_envelope_response
from apps.app_server.models.module_model import Module
from apps.app_server.serializers.module_serializer import ModuleSerializer
from apps.app_server.permissions.role_permission import IsTeacherOrAdmin
from apps.app_server.services.course_access_service import (
    is_admin_user,
    user_has_course_access,
)
from apps.app_server.services.lesson_unlock_service import get_module_state_map


class ModuleViewSet(CoreModelViewSet):
    serializer_class = ModuleSerializer
    filterset_fields = ['course']

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsAuthenticated(), IsTeacherOrAdmin()]
        return [IsAuthenticated()]

    def get_queryset(self):
        queryset = Module.objects.select_related('course').all().order_by('order_index', 'created_at')
        if self.action == 'list' and not is_admin_user(self.request.user):
            queryset = queryset.filter(course__enrollments__user=self.request.user, course__enrollments__is_deleted=False)
        return queryset

    def list(self, request, *args, **kwargs):
        course_id = request.query_params.get('course')
        if course_id and not user_has_course_access(request.user, course_id):
            return error_envelope_response(
                code=602,
                message='Bạn không có quyền truy cập khóa học này.',
                data=None,
                http_status=403,
            )
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        module = self.get_object()
        if not user_has_course_access(request.user, module.course_id):
            return error_envelope_response(
                code=602,
                message='Bạn không có quyền truy cập khóa học này.',
                data=None,
                http_status=403,
            )
        return super().retrieve(request, *args, **kwargs)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        user = self.request.user
        course_id = self.request.query_params.get('course')
        if self.action in ('list', 'retrieve') and user.is_authenticated:
            if course_id:
                context['module_state_map'] = get_module_state_map(user, course_id)
            elif self.action == 'retrieve':
                module = self.get_object()
                context['module_state_map'] = get_module_state_map(user, module.course_id)
        return context
