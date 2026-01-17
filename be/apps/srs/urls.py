from __future__ import annotations

from django.urls import include, path

from apps.srs.routes import srs_route, rse_route

urlpatterns = [
    path("srs/", include(srs_route.urlpatterns)),
    path("rse/", include(rse_route.urlpatterns)),
]
