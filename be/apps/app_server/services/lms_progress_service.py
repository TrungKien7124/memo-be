from django.utils import timezone

from apps.app_server.models.implemented.cms_lesson_model import (
    LESSON_TYPE_QUIZ,
    LESSON_TYPE_TEXT,
    LESSON_TYPE_VIDEO,
)
from apps.app_server.services.gms_xp_service import award_xp

QUIZ_MAX_HEARTS = 5


def update_lesson_progress(progress_instance, watched_seconds):
    """
    Cập nhật tiến độ xem lesson và tự động complete khi đủ thời lượng tối thiểu.

    Args:
        progress_instance: Bản ghi ``LessonProgress`` cần cập nhật.
        watched_seconds: Tổng số giây đã xem mà client/backend muốn ghi nhận.

    Returns:
        ``True`` nếu đây là lần đầu lesson được đánh dấu completed, ngược lại
        trả ``False``.

    Raises:
        Exception: Có thể phát sinh từ thao tác ``save()`` hoặc từ quá trình
            cộng XP.
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
    """
    Hoàn thành lesson không phải quiz theo rule riêng của từng loại lesson.

    Args:
        progress_instance: Bản ghi ``LessonProgress`` cần cập nhật.
        watched_seconds: Số giây xem tối đa muốn đồng bộ vào progress.
        force_complete: Chỉ áp dụng cho lesson text; nếu ``True`` thì cho phép
            complete ngay mà không cần rule thời lượng.

    Returns:
        ``True`` nếu lesson vừa mới được complete ở lần gọi này, ngược lại trả
        ``False``.

    Raises:
        Exception: Có thể phát sinh từ thao tác ``save()`` hoặc từ quá trình
            cộng XP.
    """
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


def _sync_quiz_totals(progress_instance, total_questions):
    """
    Đồng bộ các trường tổng hợp của quiz vào ``LessonProgress``.

    Args:
        progress_instance: Bản ghi progress quiz đang được xử lý.
        total_questions: Tổng số câu hỏi của quiz hiện tại.

    Returns:
        Không trả về giá trị.

    Raises:
        Không chủ động raise exception.
    """
    progress_instance.quiz_total_questions = total_questions
    progress_instance.quiz_score = progress_instance.quiz_correct_count


def _reset_quiz_runtime(progress_instance, total_questions):
    """
    Reset toàn bộ runtime state của quiz về trạng thái bắt đầu.

    Args:
        progress_instance: Bản ghi progress quiz cần reset.
        total_questions: Tổng số câu hỏi của quiz để đồng bộ lại summary.

    Returns:
        Không trả về giá trị.

    Raises:
        Không chủ động raise exception.
    """
    progress_instance.quiz_hearts_left = QUIZ_MAX_HEARTS
    progress_instance.quiz_current_question_index = 0
    progress_instance.quiz_correct_count = 0
    progress_instance.quiz_passed = False
    progress_instance.completed = False
    progress_instance.completed_at = None
    _sync_quiz_totals(progress_instance, total_questions)


def submit_quiz_answer(progress_instance, selected_answer, question_index=None):
    """
    Xử lý một lần submit đáp án quiz theo runtime rule 5 hearts.

    Args:
        progress_instance: Bản ghi ``LessonProgress`` của user cho lesson quiz.
        selected_answer: Chỉ số đáp án user chọn.
        question_index: Chỉ số câu hỏi client đang submit. Nếu không khớp với
            runtime server thì request sẽ không làm thay đổi tiến trình quiz.

    Returns:
        Dict mô tả trạng thái mới của quiz, gồm completed, failed, is_correct,
        hearts_left, current_question_index, correct_count, total_questions,
        max_hearts và newly_completed.

    Raises:
        Exception: Có thể phát sinh từ thao tác ``save()`` hoặc cộng XP khi
            quiz được hoàn thành lần đầu.
    """
    lesson = progress_instance.lesson
    if lesson.lesson_type != LESSON_TYPE_QUIZ:
        return {
            'completed': False,
            'failed': False,
            'is_correct': False,
            'hearts_left': 0,
            'current_question_index': 0,
            'correct_count': 0,
            'total_questions': 0,
            'max_hearts': QUIZ_MAX_HEARTS,
            'newly_completed': False,
        }

    questions = lesson.quiz_questions or []
    total_questions = len(questions)
    if total_questions == 0:
        _reset_quiz_runtime(progress_instance, 0)
        progress_instance.save()
        return {
            'completed': False,
            'failed': False,
            'is_correct': False,
            'hearts_left': progress_instance.quiz_hearts_left,
            'current_question_index': progress_instance.quiz_current_question_index,
            'correct_count': progress_instance.quiz_correct_count,
            'total_questions': 0,
            'max_hearts': QUIZ_MAX_HEARTS,
            'newly_completed': False,
        }

    if progress_instance.quiz_hearts_left <= 0:
        _reset_quiz_runtime(progress_instance, total_questions)

    if progress_instance.completed:
        _sync_quiz_totals(progress_instance, total_questions)
        progress_instance.save()
        return {
            'completed': True,
            'failed': False,
            'is_correct': True,
            'hearts_left': progress_instance.quiz_hearts_left,
            'current_question_index': progress_instance.quiz_current_question_index,
            'correct_count': progress_instance.quiz_correct_count,
            'total_questions': total_questions,
            'max_hearts': QUIZ_MAX_HEARTS,
            'newly_completed': False,
        }

    current_question_index = progress_instance.quiz_current_question_index
    if not isinstance(current_question_index, int) or current_question_index < 0:
        current_question_index = 0
        progress_instance.quiz_current_question_index = 0

    if current_question_index >= total_questions:
        current_question_index = total_questions - 1
        progress_instance.quiz_current_question_index = current_question_index

    submitted_question_index = current_question_index
    if isinstance(question_index, int) and 0 <= question_index < total_questions:
        submitted_question_index = question_index

    if submitted_question_index != current_question_index:
        _sync_quiz_totals(progress_instance, total_questions)
        progress_instance.save()
        return {
            'completed': progress_instance.completed,
            'failed': False,
            'is_correct': False,
            'hearts_left': progress_instance.quiz_hearts_left,
            'current_question_index': progress_instance.quiz_current_question_index,
            'correct_count': progress_instance.quiz_correct_count,
            'total_questions': total_questions,
            'max_hearts': QUIZ_MAX_HEARTS,
            'newly_completed': False,
        }

    current_question = questions[current_question_index]
    correct_index = current_question.get('correct_index')
    is_correct = isinstance(selected_answer, int) and selected_answer == correct_index
    newly_completed = False
    failed = False

    if is_correct:
        progress_instance.quiz_correct_count += 1
        progress_instance.quiz_current_question_index += 1
        if progress_instance.quiz_current_question_index >= total_questions:
            newly_completed = not progress_instance.completed
            progress_instance.quiz_passed = True
            progress_instance.completed = True
            progress_instance.completed_at = timezone.now()
            progress_instance.quiz_attempts += 1
            progress_instance.quiz_current_question_index = total_questions
    else:
        if progress_instance.quiz_hearts_left > 0:
            progress_instance.quiz_hearts_left -= 1
        if progress_instance.quiz_hearts_left == 0:
            failed = True
            progress_instance.quiz_attempts += 1
            _reset_quiz_runtime(progress_instance, total_questions)

    _sync_quiz_totals(progress_instance, total_questions)
    progress_instance.save()

    if newly_completed:
        award_xp(
            user=progress_instance.user,
            source='quiz',
            source_id=progress_instance.lesson.id,
        )

    return {
        'completed': progress_instance.completed,
        'failed': failed,
        'is_correct': is_correct,
        'hearts_left': progress_instance.quiz_hearts_left,
        'current_question_index': progress_instance.quiz_current_question_index,
        'correct_count': progress_instance.quiz_correct_count,
        'total_questions': total_questions,
        'max_hearts': QUIZ_MAX_HEARTS,
        'newly_completed': newly_completed,
    }
