from django.utils import timezone


def update_lesson_progress(progress_instance, watched_seconds):
    """
    Update watched_seconds and auto-complete when threshold is met.
    Returns True if lesson was newly completed.
    """
    progress_instance.watched_seconds = max(progress_instance.watched_seconds, watched_seconds)

    newly_completed = False
    if (
        not progress_instance.completed
        and progress_instance.watched_seconds >= progress_instance.lesson.min_watch_time
    ):
        progress_instance.completed = True
        progress_instance.completed_at = timezone.now()
        newly_completed = True

    progress_instance.save()
    return newly_completed
