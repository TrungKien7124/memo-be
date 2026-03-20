from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.app_server.models.implemented.gms_user_xp_model import UserXP
from apps.app_server.serializers.implemented.gms_serializer import UserXPSerializer
from apps.app_server.services.gms_xp_service import compute_xp_dashboard_fields


class MyXPView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user_xp, _ = UserXP.objects.get_or_create(user=request.user)
        serializer = UserXPSerializer(user_xp)
        computed = compute_xp_dashboard_fields(user=request.user)
        return Response({'data': {**serializer.data, **computed}})


class LeaderboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        period = request.query_params.get('period', 'total')
        ordering_map = {
            'weekly': '-weekly_xp',
            'monthly': '-monthly_xp',
            'total': '-total_xp',
        }
        order_field = ordering_map.get(period, '-total_xp')
        top_users = UserXP.objects.select_related('user').order_by(order_field)[:50]
        serializer = UserXPSerializer(top_users, many=True)
        return Response({'data': serializer.data})
