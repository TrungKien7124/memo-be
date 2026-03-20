from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from django.conf import settings

from apps.app_server.exceptions.exception_handler import error_response
from apps.app_server.models.implemented.iam_user_model import ROLE_STUDENT
from apps.ai.models.acs_conversation_model import Conversation
from apps.ai.services.acs_chat_service import chat_with_ai
from apps.app_server.services.lms_unlock_service import get_lesson_status_map
from apps.app_server.models.implemented.cms_lesson_model import Lesson
from apps.lesson_ingestion.services.lesson_ingestion_status_service import get_lesson_ingestion_status


class ChatView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        conversation_id = request.data.get('conversation_id')
        message_text = request.data.get('message', '').strip()
        topic = request.data.get('topic', '')
        lesson_id_raw = request.data.get('lesson_id')
        lesson_mode = 'lesson_id' in request.data

        if not message_text:
            return error_response(
                request=request,
                message='Message is required.',
                status_code=status.HTTP_400_BAD_REQUEST,
                error={'message': ['Message is required.']},
            )

        lesson = None
        if lesson_mode:
            if not lesson_id_raw:
                return error_response(
                    request=request,
                    message='lesson_id is required for lesson chat.',
                    status_code=status.HTTP_400_BAD_REQUEST,
                    error={'lesson_id': ['lesson_id is required for lesson chat.']},
                )

            lesson = Lesson.objects.filter(id=lesson_id_raw).first()
            if lesson is None:
                return error_response(
                    request=request,
                    message='Lesson not found.',
                    status_code=status.HTTP_404_NOT_FOUND,
                )

            if request.user.role == ROLE_STUDENT:
                status_map = get_lesson_status_map(request.user, lesson.module_id)
                if status_map.get(lesson.id) == 'locked':
                    return error_response(
                        request=request,
                        message='Lesson is not available.',
                        status_code=status.HTTP_403_FORBIDDEN,
                    )

        if conversation_id:
            try:
                conversation = Conversation.objects.get(id=conversation_id, user=request.user)
            except Conversation.DoesNotExist:
                return error_response(
                    request=request,
                    message='Conversation not found.',
                    status_code=status.HTTP_404_NOT_FOUND,
                )
            if lesson is not None:
                # Prevent cross-lesson history leak: reuse only when bound to the same lesson.
                if conversation.lesson_id is not None and conversation.lesson_id != lesson.id:
                    return error_response(
                        request=request,
                        message='Conversation belongs to a different lesson.',
                        status_code=status.HTTP_400_BAD_REQUEST,
                        error={
                            'conversation_id': ['Conversation belongs to a different lesson.'],
                            'lesson_id': ['Does not match the conversation lesson scope.'],
                        },
                    )
                # Bind a generic thread to a lesson only when it is still empty, so lesson-scoped
                # chat does not inherit non-lesson transcript into the LLM context.
                if conversation.lesson_id is None:
                    if conversation.messages.exists():
                        return error_response(
                            request=request,
                            message=(
                                'Cannot attach lesson context to a conversation that already has '
                                'messages from a non-lesson thread.'
                            ),
                            status_code=status.HTTP_400_BAD_REQUEST,
                            error={
                                'conversation_id': [
                                    'Conversation already has messages; start a new conversation '
                                    'for lesson chat or use one already bound to this lesson.',
                                ],
                            },
                        )
                    conversation.lesson = lesson
                    conversation.save(update_fields=['lesson', 'updated_at'])
        elif lesson is not None:
            conversation = Conversation.objects.create(user=request.user, topic=topic, lesson=lesson)
        else:
            conversation = Conversation.objects.create(user=request.user, topic=topic)

        try:
            if lesson is not None:
                rag_enabled = getattr(settings, 'AI_RAG_ENABLED', False)
                ingestion_status = get_lesson_ingestion_status(lesson)

                if not ingestion_status['supported_for_ingestion']:
                    lesson_context_status = 'unsupported_lesson'
                elif not rag_enabled:
                    lesson_context_status = 'index_failed'
                elif ingestion_status['has_active_chunk_set']:
                    lesson_context_status = 'ready'
                elif ingestion_status['latest_failed_job'] is not None:
                    lesson_context_status = 'index_failed'
                else:
                    lesson_context_status = 'index_pending'

                if lesson_context_status != 'ready':
                    return Response(
                        {
                            'data': {
                                'conversation_id': str(conversation.id),
                                'lesson_id': str(lesson.id),
                                'lesson_context_status': lesson_context_status,
                                'ai_message': None,
                            }
                        },
                        status=status.HTTP_200_OK,
                    )

                ai_message = chat_with_ai(conversation, message_text, lesson=lesson)
            else:
                ai_message = chat_with_ai(conversation, message_text)
        except RuntimeError as exc:
            return error_response(
                request=request,
                message=str(exc),
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        response_payload = {
            'conversation_id': str(conversation.id),
            'ai_message': {
                'id': str(ai_message.id),
                'role': ai_message.role,
                'content': ai_message.content,
                'created_at': ai_message.created_at.isoformat(),
            },
        }

        if lesson is not None:
            response_payload['lesson_id'] = str(lesson.id)
            response_payload['lesson_context_status'] = 'ready'

        return Response({'data': response_payload})


class ChatHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        conversations = Conversation.objects.filter(user=request.user)[:20]
        data = []
        for conv in conversations:
            data.append({
                'id': str(conv.id),
                'topic': conv.topic,
                'lesson_id': str(conv.lesson_id) if conv.lesson_id else None,
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
            return error_response(
                request=request,
                message='Conversation not found.',
                status_code=status.HTTP_404_NOT_FOUND,
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
                'lesson_id': str(conversation.lesson_id) if conversation.lesson_id else None,
                'messages': messages_data,
            }
        })
