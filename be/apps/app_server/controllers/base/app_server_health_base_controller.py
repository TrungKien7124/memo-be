from __future__ import annotations

from rest_framework.response import Response
from rest_framework.views import APIView


class BaseHealthView(APIView):
    service_name = ""

    def get(self, request):
        return Response({"service": self.service_name, "status": "ok"})
