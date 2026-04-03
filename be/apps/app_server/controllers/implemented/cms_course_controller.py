from rest_framework.permissions import IsAuthenticated
from django.db.models import Count
from django.db.models import Q

from apps.app_server.controllers.base.base_controller import CoreModelViewSet
from apps.app_server.models.implemented.cms_course_model import Course, COURSE_STATUS_PUBLISHED
from apps.app_server.serializers.implemented.cms_course_serializer import CourseSerializer
from apps.app_server.permissions.role_permission import IsTeacherOrAdmin


class CourseViewSet(CoreModelViewSet):
    serializer_class = CourseSerializer

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsAuthenticated(), IsTeacherOrAdmin()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if user.role in ('teacher', 'admin'):
            return Course.objects.annotate(
                lesson_count=Count(
                    'modules__lessons',
                    distinct=True,
                    filter=Q(modules__is_deleted=False, modules__lessons__is_deleted=False),
                ),
            )
        return Course.objects.filter(status=COURSE_STATUS_PUBLISHED).annotate(
            lesson_count=Count(
                'modules__lessons',
                distinct=True,
                filter=Q(modules__is_deleted=False, modules__lessons__is_deleted=False),
            ),
        )

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
