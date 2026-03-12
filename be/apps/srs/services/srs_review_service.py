import math
from datetime import timedelta

from django.utils import timezone


def calculate_srs_update(current_stage, current_interval, choice):
    """
    SM-2 simplified algorithm.
    Returns (new_stage, new_interval_days, new_due_date).

    EASY: stage += 2, interval *= 2.5
    GOOD: stage += 1, interval *= 1.5
    HARD: stage = 0, interval = 1
    """
    today = timezone.now().date()

    if choice == 'EASY':
        new_stage = current_stage + 2
        new_interval = max(1, math.ceil(current_interval * 2.5))
    elif choice == 'GOOD':
        new_stage = current_stage + 1
        new_interval = max(1, math.ceil(current_interval * 1.5))
    else:
        new_stage = 0
        new_interval = 1

    new_due_date = today + timedelta(days=new_interval)
    return new_stage, new_interval, new_due_date


def process_review(srs_state, choice):
    """
    Apply SRS algorithm to a CardSRSState and return log data dict.
    Also saves the updated state.
    """
    prev_stage = srs_state.stage
    prev_interval = srs_state.interval_days
    prev_due_date = srs_state.due_date

    new_stage, new_interval, new_due_date = calculate_srs_update(
        prev_stage, prev_interval, choice,
    )

    srs_state.stage = new_stage
    srs_state.interval_days = new_interval
    srs_state.due_date = new_due_date
    srs_state.last_review = timezone.now()
    srs_state.save()

    return {
        'prev_stage': prev_stage,
        'new_stage': new_stage,
        'prev_interval': prev_interval,
        'new_interval': new_interval,
        'prev_due_date': prev_due_date,
        'new_due_date': new_due_date,
    }
