from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.app_server.models.implemented.cms_lesson_model import Lesson
from apps.app_server.permissions.role_permission import IsTeacherOrAdmin
from apps.lesson_ingestion.models import LessonIngestionJobType, LessonIngestionTriggerSource
from apps.lesson_ingestion.serializers.implemented.lesson_ingestion_job_serializer import (
    LessonIngestionJobDetailSerializer,
)
from apps.lesson_ingestion.serializers.implemented.lesson_ingestion_lesson_status_serializer import (
    LessonIngestionLessonStatusSerializer,
)
from apps.lesson_ingestion.services.lesson_ingestion_scheduling_service import (
    is_ingestion_supported_lesson,
    schedule_lesson_ingestion,
)
from apps.lesson_ingestion.services.lesson_ingestion_status_service import get_lesson_ingestion_status


class LessonIngestionLessonStatusView(APIView):
    permission_classes = [IsAuthenticated, IsTeacherOrAdmin]

    def get(self, request, lesson_id):
        lesson = Lesson.objects.filter(id=lesson_id).first()
        if lesson is None:
            raise ValidationError({'lesson_id': 'Lesson not found'})

        status_payload = get_lesson_ingestion_status(lesson)
        serializer = LessonIngestionLessonStatusSerializer(status_payload)
        return Response({'data': serializer.data}, status=status.HTTP_200_OK)


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
        return Response({'data': serializer.data}, status=status.HTTP_201_CREATED)

