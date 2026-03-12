from django.urls import path

from apps.ai.controllers.acs_chat_controller import ChatView, ChatHistoryView, ConversationDetailView
from apps.ai.controllers.sps_speaking_controller import (
    SpeakingSessionCreateView,
    SpeakingTurnView,
    SpeakingSessionEndView,
)

urlpatterns = [
    path('acs/chat/', ChatView.as_view(), name='ai-chat'),
    path('acs/history/', ChatHistoryView.as_view(), name='ai-chat-history'),
    path('acs/history/<uuid:conversation_id>/', ConversationDetailView.as_view(), name='ai-conversation-detail'),
    path('sps/sessions/', SpeakingSessionCreateView.as_view(), name='speaking-session-create'),
    path('sps/speak/', SpeakingTurnView.as_view(), name='speaking-turn'),
    path('sps/sessions/<uuid:session_id>/end/', SpeakingSessionEndView.as_view(), name='speaking-session-end'),
]
