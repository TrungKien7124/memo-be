from apps.app_server.routes.base.base_route import BaseRouter
from apps.app_server.controllers.implemented.nfs_folder_controller import FolderViewSet
from apps.app_server.controllers.implemented.nfs_flashcard_controller import FlashcardViewSet

router = BaseRouter()
router.register('nfs/folders', FolderViewSet, basename='folders')
router.register('nfs/flashcards', FlashcardViewSet, basename='flashcards')

urlpatterns = router.urls
