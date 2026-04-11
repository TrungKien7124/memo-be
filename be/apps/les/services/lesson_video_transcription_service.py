import os
import subprocess
import tempfile

from apps.ai.services.providers import get_stt_provider


class LessonVideoTranscriptionError(Exception):
    pass


def _extract_audio_to_wav(video_path: str, wav_path: str) -> None:
    command = [
        'ffmpeg',
        '-y',
        '-i',
        video_path,
        '-vn',
        '-acodec',
        'pcm_s16le',
        '-ar',
        '16000',
        '-ac',
        '1',
        wav_path,
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise LessonVideoTranscriptionError(result.stderr or 'ffmpeg audio extraction failed')


def transcribe_lesson_video(*, video_path: str, language: str = 'en') -> str:
    if not video_path or not os.path.exists(video_path):
        raise LessonVideoTranscriptionError('Video file does not exist for transcription.')

    with tempfile.NamedTemporaryFile(suffix='.wav', delete=True) as temp_audio:
        _extract_audio_to_wav(video_path, temp_audio.name)
        stt_provider = get_stt_provider()
        try:
            with open(temp_audio.name, 'rb') as audio_file:
                transcript_text = stt_provider.transcribe(audio_file, language=language)
        except Exception as exc:
            raise LessonVideoTranscriptionError('Lesson video transcription failed.') from exc

    normalized = (transcript_text or '').strip()
    if not normalized:
        raise LessonVideoTranscriptionError('Transcription returned empty text.')
    return normalized
