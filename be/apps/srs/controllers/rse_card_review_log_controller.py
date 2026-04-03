from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.app_server.exceptions.exception_handler import error_response
from apps.srs.models.rse_review_session_model import ReviewSession
from apps.srs.models.srs_card_srs_state_model import CardSRSState
from apps.srs.models.rse_card_review_log_model import CardReviewLog
from apps.srs.serializers.rse_card_review_log_serializer import (
    CardReviewLogSerializer,
    CardReviewLogCreateSerializer,
)
from apps.srs.services.srs_review_service import process_review
from apps.app_server.services.gms_xp_service import award_xp


class CardReviewLogCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CardReviewLogCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            review_session = ReviewSession.objects.get(id=data['session'], user=request.user)
        except ReviewSession.DoesNotExist:
            return error_response(
                request=request,
                message='Review session not found.',
                status_code=status.HTTP_404_NOT_FOUND,
            )

        try:
            srs_state = CardSRSState.objects.select_related('card').get(
                card_id=data['card'],
                card__user=request.user,
            )
        except CardSRSState.DoesNotExist:
            return error_response(
                request=request,
                message='Card SRS state not found.',
                status_code=status.HTTP_404_NOT_FOUND,
            )

        if review_session.folder_id and srs_state.card.folder_id != review_session.folder_id:
            return error_response(
                request=request,
                message='Card does not belong to the review session folder.',
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        log_data = process_review(srs_state, data['choice'])

        review_log = CardReviewLog.objects.create(
            card_id=data['card'],
            user=request.user,
            session=review_session,
            choice=data['choice'],
            **log_data,
        )

        award_xp(user=request.user, source='review', source_id=review_log.id)

        result_serializer = CardReviewLogSerializer(review_log)
        return Response({'data': result_serializer.data}, status=status.HTTP_201_CREATED)


class CardReviewLogListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        logs = CardReviewLog.objects.filter(user=request.user).select_related('card')[:100]
        serializer = CardReviewLogSerializer(logs, many=True)
        return Response({'data': serializer.data})
