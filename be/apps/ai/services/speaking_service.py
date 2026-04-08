import logging

from apps.ai.services.providers import get_stt_provider, get_tts_provider
from apps.ai.services.chat_service import chat_with_ai

logger = logging.getLogger(__name__)


def speech_to_text(audio_file):
    """Convert audio file to text using the configured STT provider."""
    stt = get_stt_provider()
    return stt.transcribe(audio_file, language='en')


def text_to_speech(text):
    """Convert text to speech using the configured TTS provider."""
    tts = get_tts_provider()
    return tts.synthesize(text)


def process_speaking_turn(speaking_session, audio_file=None, text_input=None):
    """
    Process one speaking turn: STT -> AI Chat -> TTS.
    Falls back to text_input if audio_file STT fails.
    Returns (ai_message, audio_bytes_or_none).
    """
    user_text = text_input

    if audio_file is not None:
        try:
            user_text = speech_to_text(audio_file)
        except RuntimeError:
            if text_input is None:
                raise
            logger.info('STT failed, falling back to text input')

    if not user_text:
        raise ValueError('No input provided (audio or text).')

    ai_message = chat_with_ai(speaking_session.conversation, user_text)

    audio_bytes = None
    try:
        audio_bytes = text_to_speech(ai_message.content)
    except RuntimeError:
        logger.warning('TTS failed, returning text-only response')

    return ai_message, audio_bytes
