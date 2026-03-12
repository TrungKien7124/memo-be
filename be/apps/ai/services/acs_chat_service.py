import logging

from django.conf import settings

from openai import OpenAI

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
    """Build the messages list for the OpenAI API from conversation history."""
    api_messages = [{'role': 'system', 'content': get_system_prompt(topic)}]
    for msg in conversation_messages:
        api_messages.append({'role': msg.role, 'content': msg.content})
    return api_messages


def chat_with_ai(conversation, user_message_text):
    """
    Send user message to AI and return AI response text.
    Saves both user and AI messages to the conversation.
    Raises on AI API failure after 1 retry.
    """
    from apps.ai.models.acs_message_model import Message

    Message.objects.create(
        conversation=conversation,
        role='user',
        content=user_message_text,
    )

    history = conversation.messages.order_by('created_at')
    api_messages = build_messages_for_api(history, conversation.topic)

    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    ai_response_text = _call_openai_with_retry(client, api_messages)

    ai_message = Message.objects.create(
        conversation=conversation,
        role='assistant',
        content=ai_response_text,
    )

    return ai_message


def _call_openai_with_retry(client, messages, max_retries=1):
    """Call OpenAI API with retry on failure."""
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            response = client.chat.completions.create(
                model='gpt-3.5-turbo',
                messages=messages,
                max_tokens=500,
                temperature=0.7,
                timeout=30,
            )
            return response.choices[0].message.content
        except Exception as exc:
            last_error = exc
            logger.warning('OpenAI API attempt %d failed: %s', attempt + 1, exc)

    raise RuntimeError(f'AI service unavailable after {max_retries + 1} attempts: {last_error}')
