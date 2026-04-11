from django.db import transaction
from django.db.models import BooleanField, Count, DateTimeField, Exists, OuterRef, Q, Subquery, Value
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from apps.app_server.controllers.base_controller import CoreModelViewSet
from apps.app_server.models.course_enrollment_model import CourseEnrollment
from apps.app_server.models.course_model import Course, COURSE_STATUS_PUBLISHED
from apps.app_server.models.user_model import ROLE_TEACHER, User
from apps.app_server.permissions.role_permission import IsAdmin, IsTeacherOrAdmin
from apps.app_server.responses.api_responses import success_response, warning_envelope_response
from apps.app_server.serializers.course_enrollment_serializer import CourseEnrollmentSerializer
from apps.app_server.serializers.module_serializer import ModuleSerializer
from apps.app_server.serializers.course_serializer import CourseSerializer
from apps.app_server.serializers.course_extend_store_serializer import CourseExtendStoreSerializer
from apps.app_server.services.course_access_service import is_admin_user


class CourseViewSet(CoreModelViewSet):
    serializer_class = CourseSerializer

    def get_permissions(self):
        if self.action in (
            'enrollments',
            'revoke_enrollment',
            'bulk_grant_teachers',
        ):
            return [IsAuthenticated(), IsAdmin()]
        if self.action in ('create', 'update', 'partial_update', 'destroy', 'extend_store'):
            return [IsAuthenticated(), IsTeacherOrAdmin()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        enrollment_subquery = CourseEnrollment.objects.filter(
            user=user,
            course_id=OuterRef('pk'),
        )

        if user.role in ('teacher', 'admin'):
            base_queryset = Course.objects.annotate(
                lesson_count=Count(
                    'modules__lessons',
                    distinct=True,
                    filter=Q(modules__is_deleted=False, modules__lessons__is_deleted=False),
                ),
            )
        else:
            base_queryset = Course.objects.filter(status=COURSE_STATUS_PUBLISHED).annotate(
                lesson_count=Count(
                    'modules__lessons',
                    distinct=True,
                    filter=Q(modules__is_deleted=False, modules__lessons__is_deleted=False),
                ),
            )

        if is_admin_user(user):
            return base_queryset.annotate(
                is_enrolled=Value(True, output_field=BooleanField()),
                enrolled_at=Value(None, output_field=DateTimeField()),
            )

        return base_queryset.annotate(
            is_enrolled=Exists(enrollment_subquery),
            enrolled_at=Subquery(enrollment_subquery.values('enrolled_at')[:1]),
        )

    @action(detail=True, methods=['post'], url_path='enroll')
    def enroll(self, request, pk=None):
        course = self.get_object()
        if is_admin_user(request.user):
            return success_response(
                data={
                    'course_id': str(course.id),
                    'is_enrolled': True,
                    'enrolled_at': None,
                },
                message='Admin đã có quyền truy cập khóa học.',
            )

        enrollment, created = CourseEnrollment.objects.get_or_create(
            user=request.user,
            course=course,
            defaults={
                'source': CourseEnrollment.SOURCE_DEMO_CHECKOUT,
                'granted_by': None,
            },
        )
        return success_response(
            data={
                'course_id': str(course.id),
                'is_enrolled': True,
                'enrolled_at': enrollment.enrolled_at,
            },
            message='Đăng ký khóa học thành công.' if created else 'Bạn đã đăng ký khóa học này.',
        )

    @action(detail=True, methods=['get', 'post'], url_path='enrollments')
    def enrollments(self, request, pk=None):
        course = self.get_object()
        if request.method.lower() == 'get':
            queryset = CourseEnrollment.objects.filter(course=course).select_related('user', 'granted_by')
            serialized = CourseEnrollmentSerializer(queryset, many=True).data
            return success_response(
                data=serialized,
                message='Lấy danh sách quyền truy cập khóa học thành công.',
            )

        user_id = request.data.get('user_id')
        if not user_id:
            return warning_envelope_response(
                code=603,
                message='user_id là bắt buộc.',
                data={'old_data': request.data, 'errors': {'user_id': ['This field is required.']}},
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        target_user = User.objects.filter(id=user_id, is_deleted=False).first()
        if target_user is None:
            return warning_envelope_response(
                code=604,
                message='Người dùng không tồn tại.',
                data=None,
                http_status=status.HTTP_404_NOT_FOUND,
            )

        enrollment, created = CourseEnrollment.objects.get_or_create(
            user=target_user,
            course=course,
            defaults={
                'granted_by': request.user,
                'source': CourseEnrollment.SOURCE_ADMIN_GRANT,
            },
        )
        serialized = CourseEnrollmentSerializer(enrollment).data
        return success_response(
            data=serialized,
            message='Cấp quyền truy cập khóa học thành công.' if created else 'Người dùng đã có quyền truy cập khóa học này.',
        )

    @action(detail=True, methods=['delete'], url_path=r'enrollments/(?P<enrollment_id>[^/.]+)')
    def revoke_enrollment(self, request, pk=None, enrollment_id=None):
        course = self.get_object()
        enrollment = CourseEnrollment.objects.filter(
            id=enrollment_id,
            course=course,
        ).select_related('user').first()
        if enrollment is None:
            return warning_envelope_response(
                code=604,
                message='Quyền truy cập không tồn tại.',
                data=None,
                http_status=status.HTTP_404_NOT_FOUND,
            )

        enrollment.delete()
        return success_response(
            data=None,
            message='Thu hồi quyền truy cập khóa học thành công.',
        )

    @action(detail=True, methods=['post'], url_path='enrollments/bulk-grant-teachers')
    def bulk_grant_teachers(self, request, pk=None):
        course = self.get_object()
        teacher_ids = list(
            User.objects.filter(role=ROLE_TEACHER, is_deleted=False)
            .values_list('id', flat=True)
        )
        existing_teacher_ids = set(
            CourseEnrollment.objects.filter(course=course, user_id__in=teacher_ids)
            .values_list('user_id', flat=True)
        )
        missing_teacher_ids = [teacher_id for teacher_id in teacher_ids if teacher_id not in existing_teacher_ids]

        new_enrollments = [
            CourseEnrollment(
                user_id=teacher_id,
                course=course,
                granted_by=request.user,
                source=CourseEnrollment.SOURCE_BULK_TEACHER_GRANT,
            )
            for teacher_id in missing_teacher_ids
        ]
        if new_enrollments:
            CourseEnrollment.objects.bulk_create(new_enrollments)

        return success_response(
            data={
                'created_count': len(new_enrollments),
                'existing_count': len(existing_teacher_ids),
            },
            message='Bulk cấp quyền cho giáo viên thành công.',
        )

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['patch'], url_path='extend-store')
    def extend_store(self, request, pk=None):
        """
        Atomic update for course fields + module ordering.

        Partial reorder is supported: modules omitted from the payload keep
        their current order_index.
        """
        course = self.get_object()
        serializer = CourseExtendStoreSerializer(
            data=request.data,
            context={'course': course},
        )
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        with transaction.atomic():
            update_fields = []
            for field in ('title', 'description', 'thumbnail_url', 'status'):
                if field in validated:
                    setattr(course, field, validated[field])
                    update_fields.append(field)
            if update_fields:
                course.save(update_fields=update_fields + ['updated_at'])

            modules_payload = validated.get('modules') or []
            if modules_payload:
                modules_by_id = {
                    module.id: module
                    for module in course.modules.all()
                }
                for item in modules_payload:
                    module = modules_by_id.get(item['id'])
                    if module is None:
                        continue
                    module.order_index = item.get('order_index') or 0
                    module.save(update_fields=['order_index', 'updated_at'])

        course_data = CourseSerializer(course, context=self.get_serializer_context()).data
        modules_data = ModuleSerializer(
            course.modules.all().order_by('order_index', 'title', 'created_at'),
            many=True,
            context=self.get_serializer_context(),
        ).data
        return success_response(
            data={'course': course_data, 'modules': modules_data},
            message='Lưu thứ tự khóa học và modules thành công.',
        )
