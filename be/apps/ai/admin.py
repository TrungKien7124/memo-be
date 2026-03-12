from django.contrib import admin

from apps.ai.models.acs_conversation_model import Conversation
from apps.ai.models.acs_message_model import Message
from apps.ai.models.sps_speaking_session_model import SpeakingSession


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ['user', 'topic', 'created_at']
    search_fields = ['topic']


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['conversation', 'role', 'content_preview', 'created_at']
    list_filter = ['role']

    def content_preview(self, obj):
        return obj.content[:80]
    content_preview.short_description = 'Content'


@admin.register(SpeakingSession)
class SpeakingSessionAdmin(admin.ModelAdmin):
    list_display = ['user', 'topic_template', 'started_at', 'ended_at']
