from apps.app_server.routes.base.base_route import BaseRouter
from apps.app_server.controllers.implemented.lms_lesson_progress_controller import LessonProgressViewSet

router = BaseRouter()
router.register('lms/lesson-progress', LessonProgressViewSet, basename='lesson-progress')

urlpatterns = router.urls
