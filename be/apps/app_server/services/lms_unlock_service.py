from apps.app_server.models.implemented.cms_lesson_model import LESSON_TYPE_QUIZ, Lesson
from apps.app_server.models.implemented.cms_module_model import Module
from apps.app_server.models.implemented.lms_lesson_progress_model import LessonProgress


def get_module_state_map(user, course_id):
    modules = list(Module.objects.filter(course_id=course_id).order_by('order_index', 'created_at'))
    module_ids = [module.id for module in modules]
    if not module_ids:
        return {}

    lessons = list(
        Lesson.objects.filter(module_id__in=module_ids)
        .order_by('module_id', 'order_index', 'created_at')
    )
    lesson_ids = [lesson.id for lesson in lessons]
    progress_map = {
        progress.lesson_id: progress
        for progress in LessonProgress.objects.filter(user=user, lesson_id__in=lesson_ids)
    }

    lessons_by_module = {}
    for lesson in lessons:
        lessons_by_module.setdefault(lesson.module_id, []).append(lesson)

    final_quiz_by_module = {
        lesson.module_id: lesson
        for lesson in lessons
        if lesson.is_final and lesson.lesson_type == LESSON_TYPE_QUIZ
    }

    state_map = {}
    for index, module in enumerate(modules):
        if index == 0:
            is_unlocked = True
        else:
            previous_module = modules[index - 1]
            previous_final_quiz = final_quiz_by_module.get(previous_module.id)
            if previous_final_quiz is None:
                is_unlocked = True
            else:
                previous_progress = progress_map.get(previous_final_quiz.id)
                is_unlocked = bool(previous_progress and previous_progress.quiz_passed)

        module_lessons = lessons_by_module.get(module.id, [])
        is_completed = bool(module_lessons) and all(
            bool(progress_map.get(lesson.id) and progress_map[lesson.id].completed)
            for lesson in module_lessons
        )
        state_map[module.id] = {
            'is_unlocked': is_unlocked,
            'is_completed': is_completed,
        }

    return state_map


def get_lesson_status_map(user, module_id):
    lessons = list(Lesson.objects.filter(module_id=module_id).order_by('order_index', 'created_at'))
    if not lessons:
        return {}

    module_state_map = get_module_state_map(user, lessons[0].module.course_id)
    module_state = module_state_map.get(lessons[0].module_id, {})
    is_module_unlocked = module_state.get('is_unlocked', True)

    if not is_module_unlocked:
        return {lesson.id: 'locked' for lesson in lessons}

    progress_map = {
        progress.lesson_id: progress
        for progress in LessonProgress.objects.filter(user=user, lesson_id__in=[lesson.id for lesson in lessons])
    }

    status_map = {}
    current_assigned = False
    for lesson in lessons:
        progress = progress_map.get(lesson.id)
        if progress and progress.completed:
            status_map[lesson.id] = 'completed'
            continue
        if not current_assigned:
            status_map[lesson.id] = 'current'
            current_assigned = True
            continue
        status_map[lesson.id] = 'locked'

    return status_map
