import logging
import tempfile

from django.conf import settings

from openai import OpenAI

from apps.ai.services.acs_chat_service import chat_with_ai

logger = logging.getLogger(__name__)


def speech_to_text(audio_file):
    """
    Convert audio file to text using OpenAI Whisper API.
    Returns transcribed text or raises on failure.
    """
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    try:
        transcript = client.audio.transcriptions.create(
            model='whisper-1',
            file=audio_file,
            language='en',
        )
        return transcript.text
    except Exception as exc:
        logger.error('STT failed: %s', exc)
        raise RuntimeError('Speech-to-text failed. Please try typing your response instead.') from exc


def text_to_speech(text):
    """
    Convert text to speech using OpenAI TTS API.
    Returns audio bytes.
    """
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    try:
        response = client.audio.speech.create(
            model='tts-1',
            voice='alloy',
            input=text,
        )
        return response.content
    except Exception as exc:
        logger.error('TTS failed: %s', exc)
        raise RuntimeError('Text-to-speech failed.') from exc


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
