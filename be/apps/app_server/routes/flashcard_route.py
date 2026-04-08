from apps.app_server.routes.base_route import BaseRouter
from apps.app_server.controllers.folder_controller import FolderViewSet
from apps.app_server.controllers.flashcard_controller import FlashcardViewSet

router = BaseRouter()
router.register('folders', FolderViewSet, basename='folders')
router.register('flashcards', FlashcardViewSet, basename='flashcards')

urlpatterns = router.urls
