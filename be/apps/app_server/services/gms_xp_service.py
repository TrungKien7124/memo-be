from django.db import transaction

from apps.app_server.models.implemented.gms_xp_transaction_model import XPTransaction
from apps.app_server.models.implemented.gms_user_xp_model import UserXP

XP_AMOUNTS = {
    'lesson': 10,
    'review': 15,
    'quiz': 20,
    'speaking': 30,
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
