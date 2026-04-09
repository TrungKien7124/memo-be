import json
import mimetypes
import os

from django.core import signing
from django.core.signing import BadSignature, SignatureExpired
from django.http import FileResponse, HttpResponse
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import AllowAny, IsAuthenticated

from apps.app_server.controllers.base_controller import CoreModelViewSet
from apps.app_server.responses.api_responses import error_envelope_response, success_response
from apps.app_server.models.lesson_model import Lesson
from apps.app_server.models.module_model import Module
from apps.app_server.serializers.lesson_serializer import LessonSerializer
from apps.app_server.permissions.role_permission import IsTeacherOrAdmin
from apps.app_server.services.course_access_service import (
    is_admin_user,
    user_has_course_access,
)
from apps.app_server.services.lesson_unlock_service import get_lesson_status_map
from apps.les.models import LessonIngestionTriggerSource
from apps.les.services.lesson_ingestion_scheduling_service import (
    extract_ingestion_relevant_fields,
    schedule_lesson_index_delete,
    schedule_lesson_ingestion,
    schedule_lesson_reingestion_if_needed,
)
from apps.les.services.lesson_video_transcription_scheduling_service import (
    schedule_lesson_video_transcription,
)


class LessonViewSet(CoreModelViewSet):
    serializer_class = LessonSerializer
    filterset_fields = ['module']
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    PLAYBACK_TOKEN_SALT = 'lesson-video-playback'
    PLAYBACK_COOKIE_NAME = 'lesson_playback_session'

    def get_normalized_data(self):
        data = super().get_normalized_data().copy()
        quiz_questions_value = data.get('quiz_questions')
        if isinstance(quiz_questions_value, str):
            try:
                data['quiz_questions'] = json.loads(quiz_questions_value)
            except json.JSONDecodeError:
                pass
        return data

    def get_permissions(self):
        if self.action == 'video_stream':
            return [AllowAny()]
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsAuthenticated(), IsTeacherOrAdmin()]
        return [IsAuthenticated()]

    def get_queryset(self):
        queryset = Lesson.objects.select_related('module').all().order_by('order_index', 'created_at')
        if self.action == 'list' and not is_admin_user(self.request.user):
            queryset = queryset.filter(
                module__course__enrollments__user=self.request.user,
                module__course__enrollments__is_deleted=False,
            )
        return queryset

    def list(self, request, *args, **kwargs):
        module_id = request.query_params.get('module')
        if module_id:
            module = Module.all_objects.filter(id=module_id, is_deleted=False).select_related('course').first()
            if module and not user_has_course_access(request.user, module.course_id):
                return error_envelope_response(
                    code=602,
                    message='Bạn không có quyền truy cập khóa học này.',
                    data=None,
                    http_status=403,
                )
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        lesson = self.get_object()
        if not user_has_course_access(request.user, lesson.module.course_id):
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
        if serializer.instance.video_file:
            schedule_lesson_video_transcription(serializer.instance)
        schedule_lesson_ingestion(
            serializer.instance,
            trigger_source=LessonIngestionTriggerSource.LESSON_CREATED,
            job_type=None,
        )

    def perform_update(self, serializer):
        previous_snapshot = extract_ingestion_relevant_fields(serializer.instance)
        previous_video_file_name = serializer.instance.video_file.name if serializer.instance.video_file else ''
        super().perform_update(serializer)
        current_video_file_name = serializer.instance.video_file.name if serializer.instance.video_file else ''
        if current_video_file_name and current_video_file_name != previous_video_file_name:
            schedule_lesson_video_transcription(serializer.instance)
        schedule_lesson_reingestion_if_needed(previous_snapshot, serializer.instance)

    @action(detail=True, methods=['get'], url_path='video/playback')
    def video_playback(self, request, pk=None):
        lesson = self.get_object()
        if not user_has_course_access(request.user, lesson.module.course_id):
            return error_envelope_response(
                code=602,
                message='Bạn không có quyền truy cập khóa học này.',
                data=None,
                http_status=403,
            )
        if not lesson.video_file:
            return error_envelope_response(
                code=601,
                message='Bài học chưa có video file.',
                data=None,
                http_status=404,
            )
        token = signing.dumps(
            {'lesson_id': str(lesson.id), 'user_id': str(request.user.id)},
            salt=self.PLAYBACK_TOKEN_SALT,
        )
        response = success_response(
            data={
                'stream_url': request.build_absolute_uri(f'/api/lessons/{lesson.id}/video/stream/?token={token}'),
                'expires_in_seconds': 300,
            },
            message='Lấy playback URL thành công.',
        )
        cookie_payload = signing.dumps(
            {'lesson_id': str(lesson.id), 'user_id': str(request.user.id)},
            salt=f'{self.PLAYBACK_TOKEN_SALT}-cookie',
        )
        response.set_cookie(
            self.PLAYBACK_COOKIE_NAME,
            cookie_payload,
            max_age=300,
            httponly=True,
            samesite='Lax',
            secure=False,
        )
        return response

    @action(detail=True, methods=['get'], url_path='video/stream')
    def video_stream(self, request, pk=None):
        lesson = self.get_object()
        token = request.query_params.get('token', '')
        session_cookie = request.COOKIES.get(self.PLAYBACK_COOKIE_NAME, '')
        try:
            payload = signing.loads(token, salt=self.PLAYBACK_TOKEN_SALT, max_age=300)
            cookie_payload = signing.loads(
                session_cookie,
                salt=f'{self.PLAYBACK_TOKEN_SALT}-cookie',
                max_age=300,
            )
        except (BadSignature, SignatureExpired):
            return error_envelope_response(
                code=602,
                message='Playback token không hợp lệ hoặc đã hết hạn.',
                data=None,
                http_status=403,
            )

        if str(payload.get('lesson_id')) != str(lesson.id):
            return error_envelope_response(
                code=602,
                message='Playback token không hợp lệ cho bài học này.',
                data=None,
                http_status=403,
            )
        if str(cookie_payload.get('lesson_id')) != str(lesson.id):
            return error_envelope_response(
                code=602,
                message='Playback session không hợp lệ cho bài học này.',
                data=None,
                http_status=403,
            )
        if str(payload.get('user_id')) != str(cookie_payload.get('user_id')):
            return error_envelope_response(
                code=602,
                message='Playback session không hợp lệ cho người dùng này.',
                data=None,
                http_status=403,
            )
        if not lesson.video_file:
            return error_envelope_response(
                code=601,
                message='Bài học chưa có video file.',
                data=None,
                http_status=404,
            )

        file_path = lesson.video_file.path
        file_size = os.path.getsize(file_path)
        content_type = mimetypes.guess_type(file_path)[0] or 'video/mp4'
        range_header = request.headers.get('Range')

        if not range_header:
            response = FileResponse(open(file_path, 'rb'), content_type=content_type)
            response['Accept-Ranges'] = 'bytes'
            response['Content-Length'] = str(file_size)
            return response

        range_value = range_header.strip().lower()
        if not range_value.startswith('bytes='):
            return HttpResponse(status=416)
        start_end = range_value.replace('bytes=', '', 1).split('-', 1)
        start = int(start_end[0]) if start_end[0] else 0
        end = int(start_end[1]) if start_end[1] else file_size - 1
        end = min(end, file_size - 1)
        if start > end or start >= file_size:
            return HttpResponse(status=416)

        length = end - start + 1
        with open(file_path, 'rb') as file_obj:
            file_obj.seek(start)
            data = file_obj.read(length)
        response = HttpResponse(data, status=206, content_type=content_type)
        response['Accept-Ranges'] = 'bytes'
        response['Content-Range'] = f'bytes {start}-{end}/{file_size}'
        response['Content-Length'] = str(length)
        return response

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
        return success_response(
            data=None,
            message='Xóa bài học thành công.',
        )
