from __future__ import annotations

from django.urls import include, path

from apps.app_server.routes.base.app_server_base_router import CoreRouter
from apps.app_server.controllers.implemented.nfs_health_controller import NFSHealthView
from apps.app_server.controllers.implemented.nfs_folder_controller import FolderViewSet
from apps.app_server.controllers.implemented.nfs_flashcard_controller import FlashcardViewSet

router = CoreRouter()

router.register("folders", FolderViewSet, basename="folders")
router.register("flashcards", FlashcardViewSet, basename="flashcards")

urlpatterns = [
    path("health/", NFSHealthView.as_view(), name="nfs-health"),
    path("", include(router.urls)),
]
