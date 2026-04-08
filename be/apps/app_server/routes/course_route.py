from apps.app_server.routes.base_route import BaseRouter
from apps.app_server.controllers.course_controller import CourseViewSet

router = BaseRouter()
router.register('courses', CourseViewSet, basename='courses')

urlpatterns = router.urls
