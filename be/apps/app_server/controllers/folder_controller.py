from django.db.models import Count, Q
from rest_framework.permissions import IsAuthenticated

from apps.app_server.controllers.base_controller import CoreModelViewSet
from apps.app_server.models.folder_model import Folder
from apps.app_server.serializers.folder_serializer import FolderSerializer


class FolderViewSet(CoreModelViewSet):
    serializer_class = FolderSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ['name']

    def get_queryset(self):
        return (
            Folder.objects
            .filter(user=self.request.user)
            .annotate(flashcard_count=Count('flashcards', filter=Q(flashcards__is_deleted=False)))
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
