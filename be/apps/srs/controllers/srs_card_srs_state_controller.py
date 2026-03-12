from rest_framework.permissions import IsAuthenticated

from apps.app_server.controllers.base.base_controller import CoreModelViewSet
from apps.srs.models.srs_card_srs_state_model import CardSRSState
from apps.srs.serializers.srs_card_srs_state_serializer import CardSRSStateSerializer


class CardSRSStateViewSet(CoreModelViewSet):
    serializer_class = CardSRSStateSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = {'due_date': ['lte', 'gte', 'exact']}
    http_method_names = ['get', 'head', 'options']

    def get_queryset(self):
        return (
            CardSRSState.objects
            .filter(card__user=self.request.user, card__is_deleted=False)
            .select_related('card')
        )
