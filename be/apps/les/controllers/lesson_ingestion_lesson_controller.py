from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.app_server.models.lesson_model import Lesson
from apps.app_server.permissions.role_permission import IsTeacherOrAdmin
from apps.app_server.responses.api_responses import success_response
from apps.les.models import LessonIngestionJobType, LessonIngestionTriggerSource
from apps.les.serializers.lesson_ingestion_job_serializer import (
    LessonIngestionJobDetailSerializer,
)
from apps.les.serializers.lesson_ingestion_lesson_status_serializer import (
    LessonIngestionLessonStatusSerializer,
)
from apps.les.services.lesson_ingestion_scheduling_service import (
    is_ingestion_supported_lesson,
    schedule_lesson_ingestion,
)
from apps.les.services.lesson_ingestion_status_service import get_lesson_ingestion_status


class LessonIngestionLessonStatusView(APIView):
    permission_classes = [IsAuthenticated, IsTeacherOrAdmin]

    def get(self, request, lesson_id):
        lesson = Lesson.objects.filter(id=lesson_id).first()
        if lesson is None:
            raise ValidationError({'lesson_id': 'Lesson not found'})

        status_payload = get_lesson_ingestion_status(lesson)
        serializer = LessonIngestionLessonStatusSerializer(status_payload)
        return success_response(
            data=serializer.data,
            message='Lấy trạng thái ingestion thành công.',
            http_status=status.HTTP_200_OK,
        )


class LessonIngestionManualReindexView(APIView):
    permission_classes = [IsAuthenticated, IsTeacherOrAdmin]

    def post(self, request, lesson_id):
        lesson = Lesson.objects.filter(id=lesson_id).first()
        if lesson is None:
            raise ValidationError({'lesson_id': 'Lesson not found'})

        if not is_ingestion_supported_lesson(lesson):
            raise ValidationError('Unsupported lesson type for ingestion reindex.')

        job = schedule_lesson_ingestion(
            lesson,
            trigger_source=LessonIngestionTriggerSource.MANUAL_REINDEX,
            job_type=LessonIngestionJobType.REINGEST,
        )

        if job is None:
            raise ValidationError('Failed to create manual reindex job')

        serializer = LessonIngestionJobDetailSerializer(job)
        return success_response(
            data=serializer.data,
            message='Tạo job reindex thủ công thành công.',
            http_status=status.HTTP_201_CREATED,
        )
