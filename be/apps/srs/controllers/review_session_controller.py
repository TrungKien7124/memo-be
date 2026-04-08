from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import NotFound, ValidationError

from apps.app_server.controllers.base_controller import CoreModelViewSet
from apps.app_server.responses.api_responses import success_response
from apps.app_server.models.folder_model import Folder
from apps.srs.models.review_session_model import ReviewSession
from apps.srs.serializers.review_session_serializer import ReviewSessionSerializer


class ReviewSessionViewSet(CoreModelViewSet):
    serializer_class = ReviewSessionSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post', 'patch', 'head', 'options']

    def get_queryset(self):
        return ReviewSession.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        folder_id = request.data.get('folder') or request.data.get('folder_id')
        folder = None
        if folder_id:
            try:
                # Validate UUID early to avoid confusing errors later.
                folder_uuid = str(folder_id)
                folder = Folder.objects.filter(id=folder_uuid, user=request.user).first()
            except (ValueError, TypeError):
                raise ValidationError({'folder': 'Invalid folder id.'})

            if not folder:
                raise NotFound({'folder': 'Folder not found.'})

        session = ReviewSession.objects.create(user=request.user, folder=folder)
        serializer = self.get_serializer(session)
        return success_response(
            data=serializer.data,
            message='Tạo phiên ôn tập thành công.',
            http_status=status.HTTP_201_CREATED,
        )

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.ended_at = timezone.now()
        instance.save(update_fields=['ended_at', 'updated_at'])
        serializer = self.get_serializer(instance)
        return success_response(
            data=serializer.data,
            message='Kết thúc phiên ôn tập thành công.',
        )
