from apps.app_server.routes.base_route import BaseRouter
from apps.app_server.controllers.lesson_progress_controller import LessonProgressViewSet

router = BaseRouter()
router.register('lesson-progress', LessonProgressViewSet, basename='lesson-progress')

urlpatterns = router.urls
