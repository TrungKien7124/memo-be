from django.db import models, transaction
from rest_framework.permissions import IsAuthenticated

from apps.app_server.controllers.base_controller import CoreModelViewSet
from apps.app_server.responses.api_responses import error_envelope_response, success_response
from apps.app_server.models.module_model import Module
from apps.app_server.serializers.module_serializer import ModuleSerializer
from apps.app_server.permissions.role_permission import IsTeacherOrAdmin
from apps.app_server.services.course_access_service import (
    is_admin_user,
    user_has_course_access,
)
from apps.app_server.models.lesson_model import Lesson
from apps.app_server.serializers.lesson_serializer import LessonSerializer
from apps.app_server.serializers.module_extend_store_serializer import ModuleExtendStoreSerializer
from rest_framework.decorators import action
from apps.app_server.services.lesson_unlock_service import get_module_state_map


class ModuleViewSet(CoreModelViewSet):
    serializer_class = ModuleSerializer
    filterset_fields = ['course']

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy', 'extend_store'):
            return [IsAuthenticated(), IsTeacherOrAdmin()]
        return [IsAuthenticated()]

    def get_queryset(self):
        queryset = Module.objects.select_related('course').all().order_by('order_index', 'title', 'created_at')
        if self.action == 'list' and not is_admin_user(self.request.user):
            queryset = queryset.filter(course__enrollments__user=self.request.user, course__enrollments__is_deleted=False)
        return queryset

    def perform_create(self, serializer):
        """
        When order_index is missing or 0, append the module to the end
        of its course sequence.
        """
        course = serializer.validated_data.get('course')
        order_index = serializer.validated_data.get('order_index') or 0
        if course is not None and order_index == 0:
            max_order = (
                Module.objects.filter(course=course).aggregate(models.Max('order_index'))['order_index__max'] or 0
            )
            serializer.validated_data['order_index'] = max_order + 1
        super().perform_create(serializer)

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

    @action(detail=True, methods=['patch'], url_path='extend-store')
    def extend_store(self, request, pk=None):
        """
        Atomic update for module fields + lesson ordering.

        Partial reorder is supported: lessons omitted from the payload keep
        their current order_index.
        """
        module = self.get_object()
        serializer = ModuleExtendStoreSerializer(
            data=request.data,
            context={'module': module},
        )
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        with transaction.atomic():
            update_fields = []
            if 'title' in validated:
                module.title = validated['title']
                update_fields.append('title')
            if update_fields:
                module.save(update_fields=update_fields + ['updated_at'])

            lessons_payload = validated.get('lessons') or []
            if lessons_payload:
                lessons_by_id = {
                    lesson.id: lesson
                    for lesson in Lesson.objects.filter(module=module)
                }
                for item in lessons_payload:
                    lesson = lessons_by_id.get(item['id'])
                    if lesson is None:
                        continue
                    lesson.order_index = item.get('order_index') or 0
                    lesson.save(update_fields=['order_index', 'updated_at'])

        module_data = ModuleSerializer(module, context=self.get_serializer_context()).data
        lessons_qs = Lesson.objects.filter(module=module).order_by('order_index', 'title', 'created_at')
        lessons_data = LessonSerializer(lessons_qs, many=True, context=self.get_serializer_context()).data
        return success_response(
            data={'module': module_data, 'lessons': lessons_data},
            message='Lưu thứ tự module và lessons thành công.',
        )
