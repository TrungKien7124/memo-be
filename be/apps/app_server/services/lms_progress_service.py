from django.utils import timezone

from apps.app_server.services.gms_xp_service import award_xp


def update_lesson_progress(progress_instance, watched_seconds):
    """
    Update watched_seconds and auto-complete when threshold is met.
    Awards XP on first completion.
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

    if newly_completed:
        award_xp(
            user=progress_instance.user,
            source='lesson',
            source_id=progress_instance.lesson.id,
        )

    return newly_completed
