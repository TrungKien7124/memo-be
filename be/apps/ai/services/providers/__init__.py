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
    """
    Lấy singleton provider cho tác vụ LLM theo cấu hình hiện tại.

    Args:
        Không có tham số.

    Returns:
        Instance của provider triển khai ``BaseLLMProvider``.

    Raises:
        ValueError: Khi ``AI_PROVIDER`` có giá trị không được hỗ trợ.
    """
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
    """
    Lấy singleton provider cho tác vụ speech-to-text.

    Args:
        Không có tham số.

    Returns:
        Instance của provider triển khai ``BaseSTTProvider``.

    Raises:
        ValueError: Khi ``AI_STT_PROVIDER`` không hợp lệ hoặc không được hỗ
            trợ.
    """
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
    """
    Lấy singleton provider cho tác vụ text-to-speech.

    Args:
        Không có tham số.

    Returns:
        Instance của provider triển khai ``BaseTTSProvider``.

    Raises:
        ValueError: Khi ``AI_TTS_PROVIDER`` không hợp lệ hoặc không được hỗ
            trợ.
    """
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
    """
    Reset toàn bộ provider singleton đã cache.

    Args:
        Không có tham số.

    Returns:
        Không trả về giá trị.

    Raises:
        Không chủ động raise exception.
    """
    global _llm_instance, _stt_instance, _tts_instance
    _llm_instance = None
    _stt_instance = None
    _tts_instance = None
