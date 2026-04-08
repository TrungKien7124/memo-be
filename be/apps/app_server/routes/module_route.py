from apps.app_server.routes.base_route import BaseRouter
from apps.app_server.controllers.module_controller import ModuleViewSet

router = BaseRouter()
router.register('modules', ModuleViewSet, basename='modules')

urlpatterns = router.urls
