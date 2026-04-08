from apps.app_server.routes.base_route import BaseRouter
from apps.app_server.controllers.lesson_controller import LessonViewSet

router = BaseRouter()
router.register('lessons', LessonViewSet, basename='lessons')

urlpatterns = router.urls
