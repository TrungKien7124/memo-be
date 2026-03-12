import json
import logging

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

logger = logging.getLogger(__name__)


class SpeakingConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for realtime speaking practice.
    Handles text messages; audio is sent via REST for now.
    """

    async def connect(self):
        self.session_id = self.scope['url_route']['kwargs'].get('session_id')
        self.user = self.scope.get('user')

        if not self.user or self.user.is_anonymous:
            await self.close(code=4001)
            return

        await self.accept()
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'session_id': self.session_id,
        }))

    async def disconnect(self, close_code):
        pass

    async def receive(self, text_data=None, bytes_data=None):
        if not text_data:
            return

        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON.',
            }))
            return

        message_type = data.get('type')
        if message_type == 'chat_message':
            await self._handle_chat_message(data)
        else:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f'Unknown message type: {message_type}',
            }))

    async def _handle_chat_message(self, data):
        user_text = data.get('text', '').strip()
        if not user_text:
            return

        try:
            ai_response = await self._process_chat(user_text)
            await self.send(text_data=json.dumps({
                'type': 'ai_response',
                'content': ai_response,
            }))
        except Exception as exc:
            logger.error('WebSocket chat error: %s', exc)
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'AI service temporarily unavailable.',
            }))

    @database_sync_to_async
    def _process_chat(self, user_text):
        from apps.ai.models.sps_speaking_session_model import SpeakingSession
        from apps.ai.services.acs_chat_service import chat_with_ai

        session = SpeakingSession.objects.select_related('conversation').get(
            id=self.session_id, user=self.user,
        )
        ai_message = chat_with_ai(session.conversation, user_text)
        return ai_message.content
