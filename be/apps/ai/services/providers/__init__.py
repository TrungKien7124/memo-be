import logging

from django.conf import settings

from apps.ai.services.providers.base_llm_provider import (
    BaseLLMProvider,
    BaseSTTProvider,
    BaseTTSProvider,
)

logger = logging.getLogger(__name__)

_llm_instance = None
_stt_instance = None
_tts_instance = None

AI_PROVIDER_OPENAI = 'openai'
AI_PROVIDER_LOCAL = 'local'


def get_llm_provider():
    """Return the configured LLM provider singleton."""
    global _llm_instance
    if _llm_instance is not None:
        return _llm_instance

    provider = getattr(settings, 'AI_PROVIDER', AI_PROVIDER_OPENAI)

    if provider == AI_PROVIDER_OPENAI:
        from apps.ai.services.providers.openai_provider import OpenAILLMProvider
        _llm_instance = OpenAILLMProvider()
    elif provider == AI_PROVIDER_LOCAL:
        from apps.ai.services.providers.local_provider import LocalLLMProvider
        _llm_instance = LocalLLMProvider()
    else:
        raise ValueError(f'Unknown AI_PROVIDER: {provider}. Use "openai" or "local".')

    logger.info('LLM provider initialized: %s', provider)
    return _llm_instance


def get_stt_provider():
    """Return the configured STT provider singleton."""
    global _stt_instance
    if _stt_instance is not None:
        return _stt_instance

    provider = getattr(settings, 'AI_STT_PROVIDER', None)
    if provider is None:
        provider = getattr(settings, 'AI_PROVIDER', AI_PROVIDER_OPENAI)

    if provider == AI_PROVIDER_OPENAI:
        from apps.ai.services.providers.openai_provider import OpenAISTTProvider
        _stt_instance = OpenAISTTProvider()
    elif provider == AI_PROVIDER_LOCAL:
        from apps.ai.services.providers.local_provider import LocalSTTProvider
        _stt_instance = LocalSTTProvider()
    else:
        raise ValueError(f'Unknown AI_STT_PROVIDER: {provider}')

    logger.info('STT provider initialized: %s', provider)
    return _stt_instance


def get_tts_provider():
    """Return the configured TTS provider singleton."""
    global _tts_instance
    if _tts_instance is not None:
        return _tts_instance

    provider = getattr(settings, 'AI_TTS_PROVIDER', None)
    if provider is None:
        provider = getattr(settings, 'AI_PROVIDER', AI_PROVIDER_OPENAI)

    if provider == AI_PROVIDER_OPENAI:
        from apps.ai.services.providers.openai_provider import OpenAITTSProvider
        _tts_instance = OpenAITTSProvider()
    elif provider == AI_PROVIDER_LOCAL:
        from apps.ai.services.providers.local_provider import LocalTTSProvider
        _tts_instance = LocalTTSProvider()
    else:
        raise ValueError(f'Unknown AI_TTS_PROVIDER: {provider}')

    logger.info('TTS provider initialized: %s', provider)
    return _tts_instance


def reset_providers():
    """Reset cached provider instances. Useful for testing."""
    global _llm_instance, _stt_instance, _tts_instance
    _llm_instance = None
    _stt_instance = None
    _tts_instance = None
