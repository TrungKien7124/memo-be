from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from django.db.models import Sum
from django.utils import timezone

from apps.app_server.models.user_xp_model import UserXP
from apps.app_server.models.xp_transaction_model import XPTransaction
from apps.app_server.responses.api_responses import success_response, warning_envelope_response
from apps.app_server.serializers.xp_serializer import UserXPSerializer
from apps.app_server.services.xp_service import (
    compute_xp_dashboard_fields,
    get_month_date_range,
    get_week_date_range,
)


class MyXPView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user_xp, _ = UserXP.objects.get_or_create(user=request.user)
        serializer = UserXPSerializer(user_xp)
        computed = compute_xp_dashboard_fields(user=request.user)
        return success_response(
            data={**serializer.data, **computed},
            message='Lấy dữ liệu XP thành công.',
        )


class LeaderboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        period = request.query_params.get('period', 'total')
        if period not in {'total', 'weekly', 'monthly'}:
            return warning_envelope_response(
                code=604,
                message='Tham số period không hợp lệ.',
                data=None,
                http_status=status.HTTP_400_BAD_REQUEST,
            )

        today_date = timezone.now().date()

        if period == 'total':
            top_users = UserXP.objects.select_related('user').order_by('-total_xp')[:50]
            entries = [
                {
                    'id': str(user_xp.user.id),
                    'email': user_xp.user.email,
                    'username': user_xp.user.username,
                    'xp': user_xp.total_xp,
                    'total_xp': user_xp.total_xp,
                }
                for user_xp in top_users
            ]
            return success_response(
                data=entries,
                message='Lấy bảng xếp hạng thành công.',
            )

        if period == 'weekly':
            start_date, end_date = get_week_date_range(today_date)
        else:
            start_date, end_date = get_month_date_range(today_date)

        rows = (
            XPTransaction.objects.filter(
                created_at__date__gte=start_date,
                created_at__date__lte=end_date,
            )
            .values('user__id', 'user__email', 'user__username')
            .annotate(xp=Sum('xp_amount'))
            .order_by('-xp')[:50]
        )

        entries = [
            {
                'id': str(row['user__id']),
                'email': row.get('user__email'),
                'username': row.get('user__username'),
                'xp': row.get('xp') or 0,
                'total_xp': row.get('xp') or 0,
            }
            for row in rows
        ]

        return success_response(
            data=entries,
            message='Lấy bảng xếp hạng thành công.',
        )
