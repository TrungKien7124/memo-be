import logging
import requests

from django.conf import settings

from apps.ai.services.providers.base_llm_provider import (
    BaseLLMProvider,
    BaseSTTProvider,
    BaseTTSProvider,
)
from apps.ai.services.rag.retriever import retrieve_context

logger = logging.getLogger(__name__)


class LocalLLMProvider(BaseLLMProvider):
    """
    Provider for a self-hosted LLM (vLLM, Ollama, llama.cpp, text-generation-inference, etc.)
    via an OpenAI-compatible /v1/chat/completions endpoint.

    When RAG is enabled, relevant documents are automatically retrieved and
    injected into the prompt before calling the local model.
    """

    def __init__(self):
        self.base_url = getattr(settings, 'AI_LOCAL_LLM_URL', 'http://localhost:8080')
        self.model_name = getattr(settings, 'AI_LOCAL_LLM_MODEL', 'default')
        self.api_key = getattr(settings, 'AI_LOCAL_LLM_API_KEY', 'not-needed')
        self.timeout = getattr(settings, 'AI_LOCAL_LLM_TIMEOUT', 60)

    def chat_completion(self, messages, **kwargs):
        return self._send_request(messages, **kwargs)

    def chat_completion_with_context(self, messages, context_documents=None, **kwargs):
        if context_documents is None:
            last_user_message = next(
                (m['content'] for m in reversed(messages) if m['role'] == 'user'),
                '',
            )
            if last_user_message:
                rag_filters = kwargs.pop('rag_filters', None)
                context_documents = retrieve_context(
                    query=last_user_message,
                    filters=rag_filters,
                )

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

        return self._send_request(messages, **kwargs)

    def _send_request(self, messages, **kwargs):
        url = f"{self.base_url.rstrip('/')}/v1/chat/completions"
        payload = {
            'model': kwargs.pop('model', self.model_name),
            'messages': messages,
            'max_tokens': kwargs.pop('max_tokens', 500),
            'temperature': kwargs.pop('temperature', 0.7),
        }
        payload.update(kwargs)

        headers = {'Content-Type': 'application/json'}
        if self.api_key and self.api_key != 'not-needed':
            headers['Authorization'] = f'Bearer {self.api_key}'

        last_error = None
        for attempt in range(2):
            try:
                response = requests.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=self.timeout,
                )
                response.raise_for_status()
                data = response.json()
                return data['choices'][0]['message']['content']
            except Exception as exc:
                last_error = exc
                logger.warning('Local LLM attempt %d failed: %s', attempt + 1, exc)

        raise RuntimeError(f'Local LLM unavailable after 2 attempts: {last_error}')


class LocalSTTProvider(BaseSTTProvider):
    """
    STT provider for a self-hosted Whisper API (e.g. faster-whisper-server, whisper.cpp).
    Expects an OpenAI-compatible /v1/audio/transcriptions endpoint.
    """

    def __init__(self):
        self.base_url = getattr(settings, 'AI_LOCAL_STT_URL', 'http://localhost:8081')
        self.model_name = getattr(settings, 'AI_LOCAL_STT_MODEL', 'whisper-large-v3')
        self.timeout = getattr(settings, 'AI_LOCAL_STT_TIMEOUT', 60)

    def transcribe(self, audio_file, language='en'):
        url = f"{self.base_url.rstrip('/')}/v1/audio/transcriptions"
        try:
            response = requests.post(
                url,
                files={'file': audio_file},
                data={'model': self.model_name, 'language': language},
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json().get('text', '')
        except Exception as exc:
            logger.error('Local STT failed: %s', exc)
            raise RuntimeError('Speech-to-text failed. Please try typing your response instead.') from exc


class LocalTTSProvider(BaseTTSProvider):
    """
    TTS provider for a self-hosted TTS service (e.g. Coqui TTS, Piper).
    Expects a POST endpoint returning audio bytes.
    """

    def __init__(self):
        self.base_url = getattr(settings, 'AI_LOCAL_TTS_URL', 'http://localhost:8082')
        self.timeout = getattr(settings, 'AI_LOCAL_TTS_TIMEOUT', 60)

    def synthesize(self, text, voice='default'):
        url = f"{self.base_url.rstrip('/')}/v1/audio/speech"
        try:
            response = requests.post(
                url,
                json={'input': text, 'voice': voice},
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.content
        except Exception as exc:
            logger.error('Local TTS failed: %s', exc)
            raise RuntimeError('Text-to-speech failed.') from exc
