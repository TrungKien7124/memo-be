from django.db import connection
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from apps.app_server.responses.api_responses import success_response


class HealthCheckView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        db_ok = True
        try:
            with connection.cursor() as cursor:
                cursor.execute('SELECT 1')
        except Exception:
            db_ok = False

        return success_response(
            data={
                'status': 'healthy' if db_ok else 'degraded',
                'database': 'ok' if db_ok else 'error',
            },
            message='Kiểm tra sức khỏe dịch vụ thành công.',
        )
