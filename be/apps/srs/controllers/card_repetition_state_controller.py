import uuid

from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError

from apps.app_server.controllers.base_controller import CoreModelViewSet
from apps.srs.models.card_repetition_state_model import CardSRSState
from apps.srs.serializers.card_repetition_state_serializer import CardSRSStateSerializer


class CardSRSStateViewSet(CoreModelViewSet):
    serializer_class = CardSRSStateSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = {'due_date': ['lte', 'gte', 'exact']}
    http_method_names = ['get', 'head', 'options']

    def get_queryset(self):
        folder_id = self.request.query_params.get('folder')
        if folder_id:
            try:
                uuid.UUID(str(folder_id))
            except (ValueError, TypeError):
                raise ValidationError({'folder': 'Invalid folder id.'})

        qs = (
            CardSRSState.objects
            .filter(card__user=self.request.user, card__is_deleted=False)
            .select_related('card')
        )
        if folder_id:
            qs = qs.filter(card__folder_id=folder_id)
        return qs
