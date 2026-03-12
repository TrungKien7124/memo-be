from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ai.models.acs_conversation_model import Conversation
from apps.ai.models.acs_message_model import Message
from apps.ai.services.acs_chat_service import chat_with_ai


class ChatView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        conversation_id = request.data.get('conversation_id')
        message_text = request.data.get('message', '').strip()
        topic = request.data.get('topic', '')

        if not message_text:
            return Response(
                {'error': {'type': 'validation_error', 'message': 'Message is required.'}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if conversation_id:
            try:
                conversation = Conversation.objects.get(id=conversation_id, user=request.user)
            except Conversation.DoesNotExist:
                return Response(
                    {'error': {'type': 'not_found', 'message': 'Conversation not found.'}},
                    status=status.HTTP_404_NOT_FOUND,
                )
        else:
            conversation = Conversation.objects.create(user=request.user, topic=topic)

        try:
            ai_message = chat_with_ai(conversation, message_text)
        except RuntimeError as exc:
            return Response(
                {'error': {'type': 'ai_error', 'message': str(exc)}},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response({
            'data': {
                'conversation_id': str(conversation.id),
                'ai_message': {
                    'id': str(ai_message.id),
                    'role': ai_message.role,
                    'content': ai_message.content,
                    'created_at': ai_message.created_at.isoformat(),
                },
            }
        })


class ChatHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        conversations = Conversation.objects.filter(user=request.user)[:20]
        data = []
        for conv in conversations:
            data.append({
                'id': str(conv.id),
                'topic': conv.topic,
                'created_at': conv.created_at.isoformat(),
                'message_count': conv.messages.count(),
            })
        return Response({'data': data})


class ConversationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, conversation_id):
        try:
            conversation = Conversation.objects.get(id=conversation_id, user=request.user)
        except Conversation.DoesNotExist:
            return Response(
                {'error': {'type': 'not_found', 'message': 'Conversation not found.'}},
                status=status.HTTP_404_NOT_FOUND,
            )

        messages = conversation.messages.order_by('created_at')
        messages_data = [
            {
                'id': str(msg.id),
                'role': msg.role,
                'content': msg.content,
                'created_at': msg.created_at.isoformat(),
            }
            for msg in messages
        ]

        return Response({
            'data': {
                'id': str(conversation.id),
                'topic': conversation.topic,
                'messages': messages_data,
            }
        })
