from __future__ import annotations

from apps.app_server.controllers.base.app_server_base_controller import AppServerBaseController

from apps.app_server.models.implemented.cms_lesson_model import Lesson
from apps.app_server.normalizers import LessonInputNormalizer
from apps.app_server.serializers import LessonSerializer


class LessonViewSet(AppServerBaseController):
    model = Lesson
    serializer_class = LessonSerializer
    input_normalizer_class = LessonInputNormalizer
