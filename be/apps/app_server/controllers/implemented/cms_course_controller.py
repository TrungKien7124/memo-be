from __future__ import annotations

from apps.app_server.controllers.base.app_server_base_controller import AppServerBaseController

from apps.app_server.models.implemented.cms_course_model import Course
from apps.app_server.normalizers import CourseInputNormalizer
from apps.app_server.serializers import CourseSerializer


class CourseViewSet(AppServerBaseController):
    model = Course
    serializer_class = CourseSerializer
    input_normalizer_class = CourseInputNormalizer
