from apps.app_server.models.lesson_model import (
    Lesson,
    TRANSCRIPT_STATUS_NOT_STARTED,
)
from apps.les.tasks import process_lesson_video_transcription


def schedule_lesson_video_transcription(lesson: Lesson) -> None:
    if not lesson.video_file:
        return
    lesson.transcript_status = TRANSCRIPT_STATUS_NOT_STARTED
    lesson.transcript_error = ''
    lesson.transcript_text = ''
    lesson.save(update_fields=['transcript_status', 'transcript_error', 'transcript_text', 'updated_at'])
    process_lesson_video_transcription.delay(str(lesson.id))
