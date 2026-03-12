from django.urls import path

from apps.ai.consumers import SpeakingConsumer

websocket_urlpatterns = [
    path('ws/speaking/<uuid:session_id>/', SpeakingConsumer.as_asgi()),
]
