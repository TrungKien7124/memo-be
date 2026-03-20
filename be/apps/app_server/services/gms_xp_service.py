from datetime import timedelta

from django.db import transaction
from django.db.models import Sum
from django.db.models.functions import TruncDate
from django.utils import timezone

from apps.app_server.models.implemented.gms_xp_transaction_model import XPTransaction
from apps.app_server.models.implemented.gms_user_xp_model import UserXP

XP_AMOUNTS = {
    'lesson': 10,
    'review': 15,
    'quiz': 20,
    'speaking': 30,
}

DAILY_GOAL_XP = XP_AMOUNTS['review']


def _get_last_seven_days_dates(today_date):
    start_date = today_date - timedelta(days=6)
    return [start_date + timedelta(days=i) for i in range(7)]


def get_daily_xp_totals(user, start_date, end_date):
    """
    Returns a mapping: { date -> total_xp } for the inclusive date range.
    """
    rows = (
        XPTransaction.objects.filter(
            user=user,
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
        )
        .annotate(day=TruncDate('created_at'))
        .values('day')
        .annotate(total=Sum('xp_amount'))
    )

    return {row['day']: row['total'] or 0 for row in rows}


def compute_xp_streak_and_last7(user, daily_goal_xp=DAILY_GOAL_XP, today=None):
    today_date = today or timezone.now().date()
    dates = _get_last_seven_days_dates(today_date)
    daily_totals = get_daily_xp_totals(user, dates[0], dates[-1])

    last_seven_days = [daily_totals.get(d, 0) >= daily_goal_xp for d in dates]

    streak = 0
    for offset in range(7):
        day = today_date - timedelta(days=offset)
        if daily_totals.get(day, 0) >= daily_goal_xp:
            streak += 1
        else:
            break

    return {
        'daily_goal': daily_goal_xp,
        'today_xp': daily_totals.get(today_date, 0),
        'streak': streak,
        # ordered from oldest -> newest (today at index 6)
        'last_seven_days': last_seven_days,
    }


def award_xp(user, source, source_id=None, xp_amount=None):
    """
    Award XP to a user and update their summary.
    Uses configured amounts if xp_amount is not provided.
    """
    if xp_amount is None:
        xp_amount = XP_AMOUNTS.get(source, 0)

    if xp_amount <= 0:
        return None

    with transaction.atomic():
        xp_tx = XPTransaction.objects.create(
            user=user,
            xp_amount=xp_amount,
            source=source,
            source_id=source_id,
        )

        user_xp, _ = UserXP.objects.get_or_create(user=user)
        user_xp.total_xp += xp_amount
        user_xp.weekly_xp += xp_amount
        user_xp.monthly_xp += xp_amount
        user_xp.save(update_fields=['total_xp', 'weekly_xp', 'monthly_xp', 'updated_at'])

    return xp_tx
