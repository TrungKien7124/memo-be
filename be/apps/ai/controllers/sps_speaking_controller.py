import base64

from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ai.models.acs_conversation_model import Conversation
from apps.ai.models.sps_speaking_session_model import SpeakingSession
from apps.ai.services.sps_speaking_service import process_speaking_turn
from apps.app_server.services.gms_xp_service import award_xp


class SpeakingSessionCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        topic = request.data.get('topic', '')
        conversation = Conversation.objects.create(user=request.user, topic=topic)
        session = SpeakingSession.objects.create(
            user=request.user,
            topic_template=topic,
            conversation=conversation,
        )
        return Response({
            'data': {
                'session_id': str(session.id),
                'conversation_id': str(conversation.id),
                'topic': topic,
                'started_at': session.started_at.isoformat(),
            }
        }, status=status.HTTP_201_CREATED)


class SpeakingTurnView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        session_id = request.data.get('session_id')
        text_input = request.data.get('text', '').strip() or None
        audio_file = request.FILES.get('audio')

        if not session_id:
            return Response(
                {'error': {'type': 'validation_error', 'message': 'session_id is required.'}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            session = SpeakingSession.objects.select_related('conversation').get(
                id=session_id, user=request.user,
            )
        except SpeakingSession.DoesNotExist:
            return Response(
                {'error': {'type': 'not_found', 'message': 'Speaking session not found.'}},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            ai_message, audio_bytes = process_speaking_turn(
                session,
                audio_file=audio_file,
                text_input=text_input,
            )
        except (RuntimeError, ValueError) as exc:
            return Response(
                {'error': {'type': 'ai_error', 'message': str(exc)}},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        response_data = {
            'ai_message': {
                'id': str(ai_message.id),
                'content': ai_message.content,
                'created_at': ai_message.created_at.isoformat(),
            },
        }
        if audio_bytes:
            response_data['audio_base64'] = base64.b64encode(audio_bytes).decode('utf-8')

        return Response({'data': response_data})


class SpeakingSessionEndView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, session_id):
        try:
            session = SpeakingSession.objects.get(id=session_id, user=request.user)
        except SpeakingSession.DoesNotExist:
            return Response(
                {'error': {'type': 'not_found', 'message': 'Speaking session not found.'}},
                status=status.HTTP_404_NOT_FOUND,
            )

        session.ended_at = timezone.now()
        session.save(update_fields=['ended_at', 'updated_at'])

        award_xp(user=request.user, source='speaking', source_id=session.id)

        return Response({
            'data': {
                'session_id': str(session.id),
                'ended_at': session.ended_at.isoformat(),
            }
        })
