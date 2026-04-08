import math
from datetime import timedelta

from django.utils import timezone


def calculate_srs_update(current_stage, current_interval, choice):
    """
    Tính stage, interval và due date mới theo luật SRS đơn giản hóa.

    Args:
        current_stage: Stage hiện tại của card.
        current_interval: Khoảng cách ôn tập hiện tại, tính theo ngày.
        choice: Mức độ đánh giá của người dùng, kỳ vọng là ``EASY``, ``GOOD``
            hoặc ``HARD``.

    Returns:
        Tuple ``(new_stage, new_interval_days, new_due_date)`` sau khi áp dụng
        quy tắc:
        - EASY: stage += 2, interval *= 2.5
        - GOOD: stage += 1, interval *= 1.5
        - HARD: stage = 0, interval = 1

    Raises:
        Không chủ động raise exception. Giá trị ``choice`` ngoài danh sách trên
        sẽ được xử lý như nhánh ``HARD``.
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
    Áp dụng SRS cho một ``CardSRSState`` rồi lưu trạng thái mới vào database.

    Args:
        srs_state: Bản ghi trạng thái SRS hiện tại của flashcard.
        choice: Lựa chọn review của người dùng.

    Returns:
        Dict chứa dữ liệu trước và sau khi update để phục vụ tạo
        ``CardReviewLog``.

    Raises:
        Exception: Có thể phát sinh từ thao tác ``save()`` hoặc từ object đầu
            vào không hợp lệ.
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
