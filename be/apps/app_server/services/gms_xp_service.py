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
    """
    Sinh danh sách 7 ngày gần nhất kết thúc ở ``today_date``.

    Args:
        today_date: Ngày mốc để tính 7 ngày gần nhất.

    Returns:
        Danh sách 7 đối tượng ``date`` theo thứ tự từ cũ đến mới.

    Raises:
        Không chủ động raise exception.
    """
    start_date = today_date - timedelta(days=6)
    return [start_date + timedelta(days=i) for i in range(7)]


def get_daily_xp_totals(user, start_date, end_date):
    """
    Tính tổng XP theo từng ngày trong một khoảng ngày bao gồm cả hai đầu mút.

    Args:
        user: User cần lấy thống kê XP.
        start_date: Ngày bắt đầu.
        end_date: Ngày kết thúc.

    Returns:
        Dict dạng ``{date: total_xp}``.

    Raises:
        Exception: Có thể phát sinh từ truy vấn aggregate của database.
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
    """
    Lấy tổng XP theo ngày từ transaction sớm nhất của user đến hôm nay.

    Args:
        user: User cần thống kê.
        today_date: Ngày kết thúc thống kê.

    Returns:
        Dict dạng ``{date: total_xp}``. Nếu user chưa có transaction thì trả
        về dict rỗng.

    Raises:
        Exception: Có thể phát sinh từ truy vấn aggregate của database.
    """
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
    Tính streak và mảng boolean 7 ngày gần nhất cho dashboard XP.

    Args:
        user: User cần thống kê.
        daily_goal_xp: Mức XP tối thiểu mỗi ngày để tính đạt goal.
        today: Ngày tham chiếu tùy chọn. Nếu ``None`` sẽ dùng ngày hiện tại.

    Returns:
        Dict gồm ``daily_goal``, ``today_xp``, ``streak`` và
        ``last_seven_days``.

    Raises:
        Exception: Có thể phát sinh từ truy vấn dữ liệu XP theo ngày.
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


def get_week_date_range(today_date):
    """
    Tính khoảng ngày của tuần hiện tại theo chuẩn bắt đầu từ thứ Hai.

    Args:
        today_date: Ngày bất kỳ trong tuần cần tính.

    Returns:
        Tuple ``(start_date, end_date)`` của tuần hiện tại.

    Raises:
        Không chủ động raise exception.
    """
    # Monday-based calendar week.
    start = today_date - timedelta(days=today_date.weekday())
    end = start + timedelta(days=6)
    return start, end


def get_month_date_range(today_date):
    """
    Tính ngày đầu và cuối của tháng chứa ``today_date``.

    Args:
        today_date: Ngày bất kỳ trong tháng cần tính.

    Returns:
        Tuple ``(start_date, end_date)`` của tháng hiện tại.

    Raises:
        Không chủ động raise exception.
    """
    start = today_date.replace(day=1)
    if today_date.month == 12:
        next_month = today_date.replace(year=today_date.year + 1, month=1, day=1)
    else:
        next_month = today_date.replace(month=today_date.month + 1, day=1)
    end = next_month - timedelta(days=1)
    return start, end


def get_weekly_xp(user, today=None):
    """
    Tính tổng XP của user trong tuần hiện tại.

    Args:
        user: User cần thống kê.
        today: Ngày tham chiếu tùy chọn.

    Returns:
        Tổng XP của tuần hiện tại.

    Raises:
        Exception: Có thể phát sinh từ truy vấn aggregate database.
    """
    today_date = today or timezone.now().date()
    start_date, end_date = get_week_date_range(today_date)
    result = XPTransaction.objects.filter(
        user=user,
        created_at__date__gte=start_date,
        created_at__date__lte=end_date,
    ).aggregate(total=Sum('xp_amount'))
    return result['total'] or 0


def get_monthly_xp(user, today=None):
    """
    Tính tổng XP của user trong tháng hiện tại.

    Args:
        user: User cần thống kê.
        today: Ngày tham chiếu tùy chọn.

    Returns:
        Tổng XP của tháng hiện tại.

    Raises:
        Exception: Có thể phát sinh từ truy vấn aggregate database.
    """
    today_date = today or timezone.now().date()
    start_date, end_date = get_month_date_range(today_date)
    result = XPTransaction.objects.filter(
        user=user,
        created_at__date__gte=start_date,
        created_at__date__lte=end_date,
    ).aggregate(total=Sum('xp_amount'))
    return result['total'] or 0


def compute_xp_dashboard_fields(user, today=None):
    """
    Tổng hợp các field XP cần cho dashboard từ nhiều hàm thống kê khác nhau.

    Args:
        user: User cần lấy dữ liệu dashboard.
        today: Ngày tham chiếu tùy chọn.

    Returns:
        Dict chứa daily goal, today XP, streak, last seven days, weekly XP và
        monthly XP.

    Raises:
        Exception: Có thể phát sinh từ các hàm thống kê được gọi bên trong.
    """
    streak_fields = compute_xp_streak_and_last7(user, today=today)
    return {
        **streak_fields,
        'weekly_xp': get_weekly_xp(user, today=today),
        'monthly_xp': get_monthly_xp(user, today=today),
    }


def award_xp(user, source, source_id=None, xp_amount=None):
    """
    Tạo transaction XP mới và cộng dồn vào bảng tổng hợp ``UserXP``.

    Args:
        user: User được cộng XP.
        source: Nguồn sinh XP như ``lesson``, ``review``, ``quiz`` hoặc
            ``speaking``.
        source_id: ID thực thể liên quan tới transaction XP.
        xp_amount: Số XP muốn cộng trực tiếp. Nếu ``None`` sẽ dùng mapping mặc
            định theo ``source``.

    Returns:
        Đối tượng ``XPTransaction`` vừa được tạo, hoặc ``None`` nếu số XP cần
        cộng nhỏ hơn hoặc bằng 0.

    Raises:
        Exception: Có thể phát sinh từ transaction database hoặc thao tác tạo/
            cập nhật model.
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
