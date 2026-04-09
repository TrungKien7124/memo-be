from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from apps.app_server.controllers.base_controller import CoreModelViewSet
from apps.app_server.models.lesson_comment_model import LessonComment
from apps.app_server.models.lesson_model import Lesson
from apps.app_server.responses.api_responses import (
    error_envelope_response,
    success_response,
    warning_envelope_response,
)
from apps.app_server.serializers.lesson_comment_serializer import LessonCommentSerializer
from apps.app_server.services.course_access_service import is_admin_user, user_has_lesson_access


class LessonCommentViewSet(CoreModelViewSet):
    serializer_class = LessonCommentSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['lesson']

    def get_queryset(self):
        return LessonComment.all_objects.select_related('lesson', 'user', 'parent').order_by('created_at')

    def list(self, request, *args, **kwargs):
        lesson_id = request.query_params.get('lesson')
        if not lesson_id:
            return warning_envelope_response(
                code=603,
                message='lesson là bắt buộc.',
                data={'old_data': request.query_params, 'errors': {'lesson': ['This field is required.']}},
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        if not user_has_lesson_access(request.user, lesson_id):
            return error_envelope_response(
                code=602,
                message='Bạn không có quyền truy cập bài học này.',
                data=None,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        queryset = self.filter_queryset(self.get_queryset().filter(lesson_id=lesson_id))
        serializer = self.get_serializer(queryset, many=True)
        return success_response(data=serializer.data, message='Lấy danh sách bình luận thành công.')

    def create(self, request, *args, **kwargs):
        lesson_id = request.data.get('lesson')
        if not lesson_id:
            return warning_envelope_response(
                code=603,
                message='lesson là bắt buộc.',
                data={'old_data': request.data, 'errors': {'lesson': ['This field is required.']}},
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        if not user_has_lesson_access(request.user, lesson_id):
            return error_envelope_response(
                code=602,
                message='Bạn không có quyền truy cập bài học này.',
                data=None,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        if not Lesson.all_objects.filter(id=lesson_id, is_deleted=False).exists():
            return warning_envelope_response(
                code=604,
                message='Bài học không tồn tại.',
                data=None,
                http_status=status.HTTP_404_NOT_FOUND,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)
        return success_response(
            data=serializer.data,
            message='Tạo bình luận thành công.',
            http_status=status.HTTP_201_CREATED,
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        if not user_has_lesson_access(request.user, instance.lesson_id):
            return error_envelope_response(
                code=602,
                message='Bạn không có quyền truy cập bài học này.',
                data=None,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        serializer = self.get_serializer(instance)
        return success_response(data=serializer.data, message='Lấy bình luận thành công.')

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.is_deleted:
            return warning_envelope_response(
                code=604,
                message='Bình luận đã bị xóa.',
                data=None,
                http_status=status.HTTP_404_NOT_FOUND,
            )
        if not (is_admin_user(request.user) or instance.user_id == request.user.id):
            return error_envelope_response(
                code=602,
                message='Bạn không có quyền chỉnh sửa bình luận này.',
                data=None,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        if not user_has_lesson_access(request.user, instance.lesson_id):
            return error_envelope_response(
                code=602,
                message='Bạn không có quyền truy cập bài học này.',
                data=None,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        if 'content' not in request.data:
            return warning_envelope_response(
                code=603,
                message='content là bắt buộc.',
                data={'old_data': request.data, 'errors': {'content': ['This field is required.']}},
                http_status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(instance, data={'content': request.data.get('content')}, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(edited_at=timezone.now())
        return success_response(data=serializer.data, message='Cập nhật bình luận thành công.')

    def update(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if not (is_admin_user(request.user) or instance.user_id == request.user.id):
            return error_envelope_response(
                code=602,
                message='Bạn không có quyền xóa bình luận này.',
                data=None,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        if not user_has_lesson_access(request.user, instance.lesson_id):
            return error_envelope_response(
                code=602,
                message='Bạn không có quyền truy cập bài học này.',
                data=None,
                http_status=status.HTTP_403_FORBIDDEN,
            )
        if instance.is_deleted:
            return success_response(data=None, message='Bình luận đã được xóa trước đó.')

        instance.is_deleted = True
        instance.content = ''
        instance.edited_at = timezone.now()
        instance.save(update_fields=['is_deleted', 'content', 'edited_at', 'updated_at'])
        return success_response(data=None, message='Xóa bình luận thành công.')
