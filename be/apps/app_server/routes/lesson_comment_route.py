from apps.app_server.controllers.lesson_comment_controller import LessonCommentViewSet
from apps.app_server.routes.base_route import BaseRouter

router = BaseRouter()
router.register('lesson-comments', LessonCommentViewSet, basename='lesson-comments')

urlpatterns = router.urls
