from __future__ import annotations

from django.urls import include, path

from apps.ai.routes import acs_route, sps_route

urlpatterns = [
    path("acs/", include(acs_route.urlpatterns)),
    path("sps/", include(sps_route.urlpatterns)),
]
