from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.app_server.controllers.base.base_controller import CoreModelViewSet
from apps.srs.models.rse_review_session_model import ReviewSession
from apps.srs.serializers.rse_review_session_serializer import ReviewSessionSerializer


class ReviewSessionViewSet(CoreModelViewSet):
    serializer_class = ReviewSessionSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post', 'patch', 'head', 'options']

    def get_queryset(self):
        return ReviewSession.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        session = ReviewSession.objects.create(user=request.user)
        serializer = self.get_serializer(session)
        return Response({'data': serializer.data}, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.ended_at = timezone.now()
        instance.save(update_fields=['ended_at', 'updated_at'])
        serializer = self.get_serializer(instance)
        return Response({'data': serializer.data})
