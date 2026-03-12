from apps.app_server.routes.base.base_route import BaseRouter
from apps.app_server.controllers.implemented.cms_course_controller import CourseViewSet
from apps.app_server.controllers.implemented.cms_module_controller import ModuleViewSet
from apps.app_server.controllers.implemented.cms_lesson_controller import LessonViewSet

router = BaseRouter()
router.register('cms/courses', CourseViewSet, basename='courses')
router.register('cms/modules', ModuleViewSet, basename='modules')
router.register('cms/lessons', LessonViewSet, basename='lessons')

urlpatterns = router.urls
