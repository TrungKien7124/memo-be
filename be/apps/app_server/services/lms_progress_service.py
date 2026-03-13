from django.utils import timezone

from apps.app_server.models.implemented.cms_lesson_model import (
    LESSON_TYPE_QUIZ,
    LESSON_TYPE_TEXT,
    LESSON_TYPE_VIDEO,
)
from apps.app_server.services.gms_xp_service import award_xp

QUIZ_PASS_THRESHOLD_PERCENT = 80


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


def complete_non_quiz_lesson(progress_instance, watched_seconds=0, force_complete=False):
    lesson_type = progress_instance.lesson.lesson_type
    if lesson_type == LESSON_TYPE_QUIZ:
        return False

    progress_instance.watched_seconds = max(progress_instance.watched_seconds, watched_seconds)

    if lesson_type == LESSON_TYPE_TEXT and force_complete:
        newly_completed = not progress_instance.completed
        progress_instance.completed = True
        if newly_completed:
            progress_instance.completed_at = timezone.now()
    elif lesson_type == LESSON_TYPE_VIDEO:
        newly_completed = update_lesson_progress(progress_instance, progress_instance.watched_seconds)
        return newly_completed
    else:
        newly_completed = False

    progress_instance.save()

    if newly_completed:
        award_xp(
            user=progress_instance.user,
            source='lesson',
            source_id=progress_instance.lesson.id,
        )

    return newly_completed


def submit_quiz_lesson(progress_instance, selected_answers):
    lesson = progress_instance.lesson
    if lesson.lesson_type != LESSON_TYPE_QUIZ:
        return {'score': 0, 'total_questions': 0, 'passed': False, 'newly_passed': False}

    questions = lesson.quiz_questions or []
    if not isinstance(selected_answers, list):
        selected_answers = []

    total_questions = len(questions)
    score = 0
    for index, question in enumerate(questions):
        correct_index = question.get('correct_index')
        selected = selected_answers[index] if index < len(selected_answers) else None
        if isinstance(selected, int) and selected == correct_index:
            score += 1

    passed = total_questions > 0 and ((score / total_questions) * 100) >= QUIZ_PASS_THRESHOLD_PERCENT
    newly_passed = not progress_instance.quiz_passed and passed

    progress_instance.quiz_attempts += 1
    progress_instance.quiz_score = score
    progress_instance.quiz_total_questions = total_questions
    progress_instance.quiz_passed = passed
    progress_instance.completed = passed
    if passed:
        if not progress_instance.completed_at:
            progress_instance.completed_at = timezone.now()
    else:
        progress_instance.completed_at = None
    progress_instance.save()

    if newly_passed:
        award_xp(
            user=progress_instance.user,
            source='quiz',
            source_id=progress_instance.lesson.id,
        )

    return {
        'score': score,
        'total_questions': total_questions,
        'passed': passed,
        'newly_passed': newly_passed,
    }
