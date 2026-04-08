from django.urls import path

from apps.ai.controllers.chat_controller import ChatView, ChatHistoryView, ConversationDetailView
from apps.ai.controllers.speaking_controller import (
    SpeakingSessionCreateView,
    SpeakingTurnView,
    SpeakingSessionEndView,
)

urlpatterns = [
    path('chat/', ChatView.as_view(), name='ai-chat'),
    path('conversations/', ChatHistoryView.as_view(), name='ai-chat-history'),
    path('conversations/<uuid:conversation_id>/', ConversationDetailView.as_view(), name='ai-conversation-detail'),
    path('speaking-sessions/', SpeakingSessionCreateView.as_view(), name='speaking-session-create'),
    path('speaking-turns/', SpeakingTurnView.as_view(), name='speaking-turn'),
    path('speaking-sessions/<uuid:session_id>/end/', SpeakingSessionEndView.as_view(), name='speaking-session-end'),
]
