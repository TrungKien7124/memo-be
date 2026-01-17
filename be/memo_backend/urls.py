from __future__ import annotations

from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path


def healthcheck(_request):
    return JsonResponse({"status": "ok", "service": "memo-backend"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", healthcheck, name="healthcheck"),
    path("api/", include("apps.app_server.urls")),
    path("api/", include("apps.srs.urls")),
    path("api/", include("apps.ai.urls")),
]
