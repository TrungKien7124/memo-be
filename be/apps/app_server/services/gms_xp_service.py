from datetime import timedelta

from django.db import transaction
from django.db.models import Min, Sum
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


def _get_daily_xp_totals_from_earliest_transaction(user, today_date):
    earliest_dt = XPTransaction.objects.filter(user=user).aggregate(Min('created_at'))['created_at__min']
    if not earliest_dt:
        return {}

    earliest_date = earliest_dt.date()
    rows = (
        XPTransaction.objects.filter(
            user=user,
            created_at__date__gte=earliest_date,
            created_at__date__lte=today_date,
        )
        .annotate(day=TruncDate('created_at'))
        .values('day')
        .annotate(total=Sum('xp_amount'))
    )
    return {row['day']: row['total'] or 0 for row in rows}


def compute_xp_streak_and_last7(user, daily_goal_xp=DAILY_GOAL_XP, today=None):
    """
    Streak is consecutive days ending today where daily XP >= daily_goal_xp.
    Unlike last_seven_days, streak is NOT capped to 7 days.
    """
    today_date = today or timezone.now().date()
    daily_totals = _get_daily_xp_totals_from_earliest_transaction(user, today_date)

    dates = _get_last_seven_days_dates(today_date)
    last_seven_days = [daily_totals.get(d, 0) >= daily_goal_xp for d in dates]

    streak = 0
    day = today_date
    while daily_totals.get(day, 0) >= daily_goal_xp:
        streak += 1
        day -= timedelta(days=1)

    return {
        'daily_goal': daily_goal_xp,
        'today_xp': daily_totals.get(today_date, 0),
        'streak': streak,
        # ordered from oldest -> newest (today at index 6)
        'last_seven_days': last_seven_days,
    }


def _get_week_date_range(today_date):
    # Monday-based calendar week.
    start = today_date - timedelta(days=today_date.weekday())
    end = start + timedelta(days=6)
    return start, end


def _get_month_date_range(today_date):
    start = today_date.replace(day=1)
    if today_date.month == 12:
        next_month = today_date.replace(year=today_date.year + 1, month=1, day=1)
    else:
        next_month = today_date.replace(month=today_date.month + 1, day=1)
    end = next_month - timedelta(days=1)
    return start, end


def get_weekly_xp(user, today=None):
    today_date = today or timezone.now().date()
    start_date, end_date = _get_week_date_range(today_date)
    result = XPTransaction.objects.filter(
        user=user,
        created_at__date__gte=start_date,
        created_at__date__lte=end_date,
    ).aggregate(total=Sum('xp_amount'))
    return result['total'] or 0


def get_monthly_xp(user, today=None):
    today_date = today or timezone.now().date()
    start_date, end_date = _get_month_date_range(today_date)
    result = XPTransaction.objects.filter(
        user=user,
        created_at__date__gte=start_date,
        created_at__date__lte=end_date,
    ).aggregate(total=Sum('xp_amount'))
    return result['total'] or 0


def compute_xp_dashboard_fields(user, today=None):
    streak_fields = compute_xp_streak_and_last7(user, today=today)
    return {
        **streak_fields,
        'weekly_xp': get_weekly_xp(user, today=today),
        'monthly_xp': get_monthly_xp(user, today=today),
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
