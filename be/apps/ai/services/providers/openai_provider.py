import logging

from django.conf import settings
from openai import OpenAI

from apps.ai.services.providers.base_llm_provider import (
    BaseLLMProvider,
    BaseSTTProvider,
    BaseTTSProvider,
)

logger = logging.getLogger(__name__)


class OpenAILLMProvider(BaseLLMProvider):

    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.default_model = getattr(settings, 'AI_LLM_MODEL', 'gpt-3.5-turbo')

    def chat_completion(self, messages, **kwargs):
        model = kwargs.pop('model', self.default_model)
        max_tokens = kwargs.pop('max_tokens', 500)
        temperature = kwargs.pop('temperature', 0.7)
        return self._call_with_retry(messages, model, max_tokens, temperature)

    def chat_completion_with_context(self, messages, context_documents=None, **kwargs):
        if context_documents:
            context_block = "\n\n---\n\n".join(context_documents)
            rag_message = {
                'role': 'system',
                'content': (
                    "Use the following reference documents to inform your response. "
                    "If the documents are not relevant, rely on your own knowledge.\n\n"
                    f"{context_block}"
                ),
            }
            messages = [messages[0], rag_message] + messages[1:]
        return self.chat_completion(messages, **kwargs)

    def _call_with_retry(self, messages, model, max_tokens, temperature, max_retries=1):
        last_error = None
        for attempt in range(max_retries + 1):
            try:
                response = self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    timeout=30,
                )
                return response.choices[0].message.content
            except Exception as exc:
                last_error = exc
                logger.warning('OpenAI LLM attempt %d failed: %s', attempt + 1, exc)
        raise RuntimeError(f'OpenAI LLM unavailable after {max_retries + 1} attempts: {last_error}')


class OpenAISTTProvider(BaseSTTProvider):

    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.default_model = getattr(settings, 'AI_STT_MODEL', 'whisper-1')

    def transcribe(self, audio_file, language='en'):
        try:
            transcript = self.client.audio.transcriptions.create(
                model=self.default_model,
                file=audio_file,
                language=language,
            )
            return transcript.text
        except Exception as exc:
            logger.error('OpenAI STT failed: %s', exc)
            raise RuntimeError('Speech-to-text failed. Please try typing your response instead.') from exc


class OpenAITTSProvider(BaseTTSProvider):

    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.default_model = getattr(settings, 'AI_TTS_MODEL', 'tts-1')

    def synthesize(self, text, voice='alloy'):
        try:
            response = self.client.audio.speech.create(
                model=self.default_model,
                voice=voice,
                input=text,
            )
            return response.content
        except Exception as exc:
            logger.error('OpenAI TTS failed: %s', exc)
            raise RuntimeError('Text-to-speech failed.') from exc
