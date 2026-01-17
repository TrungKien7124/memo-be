from __future__ import annotations

from apps.app_server.controllers.base.app_server_base_controller import AppServerBaseController

from apps.app_server.models.implemented.lms_lesson_progress_model import LessonProgress
from apps.app_server.normalizers import LessonProgressInputNormalizer
from apps.app_server.serializers import LessonProgressSerializer


class LessonProgressViewSet(AppServerBaseController):
    model = LessonProgress
    serializer_class = LessonProgressSerializer
    input_normalizer_class = LessonProgressInputNormalizer
