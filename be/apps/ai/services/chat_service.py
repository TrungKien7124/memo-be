import logging

from django.conf import settings

from apps.ai.services.providers import get_llm_provider
from apps.ai.services.rag.retriever import retrieve_context

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are an English conversation partner. Help the user practice English. "
    "Adapt your responses to the user's level. Correct mistakes gently. "
    "Keep responses concise and conversational."
)

TOPIC_PROMPTS = {
    'ordering_food': "The user wants to practice ordering food at a restaurant. Start the conversation as a waiter.",
    'job_interview': "The user wants to practice a job interview. Start as the interviewer.",
    'travel': "The user wants to practice travel conversations. Start as a helpful local.",
    'daily_routine': "Help the user practice talking about their daily routine.",
    'shopping': "The user wants to practice shopping conversations. Start as a store clerk.",
}


def get_system_prompt(topic=''):
    """
    Tạo system prompt cơ sở cho cuộc hội thoại AI.

    Args:
        topic: Chủ đề hội thoại hiện tại. Nếu có mapping trong
            ``TOPIC_PROMPTS`` thì prompt sẽ được bổ sung ngữ cảnh kịch bản.

    Returns:
        Chuỗi prompt hoàn chỉnh để gửi cho LLM.

    Raises:
        Không chủ động raise exception. Hàm chỉ đọc dữ liệu cấu hình tĩnh
        trong module.
    """
    topic_addition = TOPIC_PROMPTS.get(topic, '')
    if topic_addition:
        return f"{SYSTEM_PROMPT}\n\nScenario: {topic_addition}"
    return SYSTEM_PROMPT


def build_messages_for_api(conversation_messages, topic=''):
    """
    Chuẩn hóa lịch sử hội thoại về định dạng message list cho LLM provider.

    Args:
        conversation_messages: Queryset hoặc iterable các message đã lưu trong
            hội thoại. Mỗi phần tử cần có ``role`` và ``content``.
        topic: Chủ đề hội thoại để tạo system prompt phù hợp.

    Returns:
        Danh sách dict theo format ``{'role': ..., 'content': ...}``, trong đó
        phần tử đầu tiên luôn là system prompt.

    Raises:
        AttributeError: Có thể phát sinh nếu phần tử trong
            ``conversation_messages`` không có ``role`` hoặc ``content``.
    """
    api_messages = [{'role': 'system', 'content': get_system_prompt(topic)}]
    for msg in conversation_messages:
        api_messages.append({'role': msg.role, 'content': msg.content})
    return api_messages


def chat_with_ai(conversation, user_message_text, *, lesson=None):
    """
    Gửi tin nhắn người dùng tới AI, lưu lịch sử hội thoại, rồi trả về message AI.

    Args:
        conversation: Bản ghi hội thoại hiện tại. Hàm sẽ lưu cả message của
            user lẫn message phản hồi của assistant vào hội thoại này.
        user_message_text: Nội dung text do người dùng gửi lên.
        lesson: Lesson scope tùy chọn. Nếu có và RAG đang bật, hàm sẽ chỉ
            retrieve context của lesson và active ingestion job hiện hành.

    Returns:
        Đối tượng ``Message`` của assistant vừa được tạo và lưu vào database.

    Raises:
        Exception: Có thể phát sinh từ provider, truy vấn database, hoặc
            retrieval layer. Hàm này không tự catch các lỗi đó để controller
            quyết định cách phản hồi API.
    """
    from apps.ai.models.conversation_message_model import Message

    Message.objects.create(
        conversation=conversation,
        role='user',
        content=user_message_text,
    )

    history = conversation.messages.order_by('created_at')
    api_messages = build_messages_for_api(history, conversation.topic)

    llm = get_llm_provider()

    rag_enabled = getattr(settings, 'AI_RAG_ENABLED', False)
    if rag_enabled:
        if lesson is not None:
            from apps.les.models import LessonContentChunk

            active_ingestion_job_id = (
                LessonContentChunk.objects.filter(lesson=lesson, is_active=True)
                .values_list('ingestion_job_id', flat=True)
                .first()
            )

            lesson_filters = {'lesson_id': str(lesson.id)}
            if active_ingestion_job_id:
                lesson_filters['ingestion_job_id'] = str(active_ingestion_job_id)

            context_docs = retrieve_context(query=user_message_text, filters=lesson_filters)
        else:
            context_docs = retrieve_context(query=user_message_text)
        ai_response_text = llm.chat_completion_with_context(
            api_messages,
            context_documents=context_docs,
        )
    else:
        ai_response_text = llm.chat_completion(api_messages)

    ai_message = Message.objects.create(
        conversation=conversation,
        role='assistant',
        content=ai_response_text,
    )

    return ai_message
