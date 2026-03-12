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
    topic_addition = TOPIC_PROMPTS.get(topic, '')
    if topic_addition:
        return f"{SYSTEM_PROMPT}\n\nScenario: {topic_addition}"
    return SYSTEM_PROMPT


def build_messages_for_api(conversation_messages, topic=''):
    """Build the messages list for the LLM provider from conversation history."""
    api_messages = [{'role': 'system', 'content': get_system_prompt(topic)}]
    for msg in conversation_messages:
        api_messages.append({'role': msg.role, 'content': msg.content})
    return api_messages


def chat_with_ai(conversation, user_message_text):
    """
    Send user message to AI and return AI response text.
    Saves both user and AI messages to the conversation.
    When RAG is enabled, relevant context is retrieved and injected automatically.
    """
    from apps.ai.models.acs_message_model import Message

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
