from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.app_server.models.lesson_model import LESSON_TYPE_LESSON, Lesson
from apps.app_server.permissions.role_permission import IsTeacherOrAdmin
from apps.app_server.responses.api_responses import success_response
from apps.app_server.services.lesson_publication_service import reconcile_lesson_publication
from apps.les.models import LessonIngestionJobType, LessonIngestionTriggerSource
from apps.les.serializers.lesson_ingestion_job_serializer import (
    LessonIngestionJobDetailSerializer,
)
from apps.les.serializers.lesson_ingestion_lesson_status_serializer import (
    LessonIngestionLessonStatusBatchRequestSerializer,
    LessonIngestionLessonStatusSerializer,
)
from apps.les.services.lesson_ingestion_scheduling_service import (
    is_ingestion_supported_lesson,
    schedule_lesson_ingestion,
)
from apps.les.services.lesson_ingestion_status_service import (
    get_admin_lesson_pipeline_status,
    get_admin_lesson_pipeline_status_batch,
)
from apps.les.services.lesson_video_transcription_scheduling_service import (
    schedule_lesson_video_transcription,
)


class LessonIngestionLessonStatusView(APIView):
    permission_classes = [IsAuthenticated, IsTeacherOrAdmin]

    def get(self, request, lesson_id):
        lesson = Lesson.objects.filter(id=lesson_id).first()
        if lesson is None:
            raise ValidationError({'lesson_id': 'Lesson not found'})

        status_payload = get_admin_lesson_pipeline_status(lesson)
        serializer = LessonIngestionLessonStatusSerializer(status_payload)
        return success_response(
            data=serializer.data,
            message='Lấy trạng thái ingestion thành công.',
            http_status=status.HTTP_200_OK,
        )


class LessonIngestionLessonStatusBatchView(APIView):
    permission_classes = [IsAuthenticated, IsTeacherOrAdmin]

    def post(self, request):
        request_serializer = LessonIngestionLessonStatusBatchRequestSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)
        ordered_ids = request_serializer.validated_data['lesson_ids']
        batch = get_admin_lesson_pipeline_status_batch(ordered_ids)
        records_serializer = LessonIngestionLessonStatusSerializer(batch['records'], many=True)
        return success_response(
            data={
                'records': records_serializer.data,
                'missing_lesson_ids': batch['missing_lesson_ids'],
            },
            message='Lấy trạng thái ingestion (batch) thành công.',
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


class LessonVideoTranscriptRetryView(APIView):
    permission_classes = [IsAuthenticated, IsTeacherOrAdmin]

    def post(self, request, lesson_id):
        lesson = Lesson.objects.filter(id=lesson_id).first()
        if lesson is None:
            raise ValidationError({'lesson_id': 'Lesson not found'})
        if lesson.lesson_type != LESSON_TYPE_LESSON:
            raise ValidationError({'lesson_type': 'Transcript retry is only supported for lesson type.'})
        if not lesson.video_file:
            raise ValidationError({'video_file': 'Lesson does not have an uploaded video file.'})

        schedule_lesson_video_transcription(lesson)
        reconcile_lesson_publication(lesson)
        lesson.refresh_from_db()

        return success_response(
            data={
                'lesson_id': lesson.id,
                'transcript_status': lesson.transcript_status,
                'publication_status': lesson.publication_status,
                'is_active': lesson.is_active,
            },
            message='Retry lesson transcript thành công.',
            http_status=status.HTTP_200_OK,
        )
