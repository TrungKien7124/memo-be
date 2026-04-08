from django.urls import path

from apps.les.controllers.lesson_ingestion_lesson_controller import (
    LessonIngestionLessonStatusView,
    LessonIngestionManualReindexView,
)
from apps.les.controllers.lesson_ingestion_job_controller import LessonIngestionJobViewSet
from apps.app_server.routes.base_route import BaseRouter

router = BaseRouter()
router.register('lesson-ingestion/jobs', LessonIngestionJobViewSet, basename='lesson-ingestion-jobs')

urlpatterns = router.urls + [
    path(
        'lesson-ingestion/lessons/<uuid:lesson_id>/status/',
        LessonIngestionLessonStatusView.as_view(),
        name='lesson-ingestion-lesson-status',
    ),
    path(
        'lesson-ingestion/lessons/<uuid:lesson_id>/reindex/',
        LessonIngestionManualReindexView.as_view(),
        name='lesson-ingestion-manual-reindex',
    ),
]

