from __future__ import annotations

from django.urls import include, path

from apps.app_server.routes import iam_route, cms_route, lms_route, nfs_route, soc_route, gms_route, nts_route, adm_route

urlpatterns = [
    path("iam/", include(iam_route.urlpatterns)),
    path("cms/", include(cms_route.urlpatterns)),
    path("lms/", include(lms_route.urlpatterns)),
    path("nfs/", include(nfs_route.urlpatterns)),
    path("soc/", include(soc_route.urlpatterns)),
    path("gms/", include(gms_route.urlpatterns)),
    path("nts/", include(nts_route.urlpatterns)),
    path("adm/", include(adm_route.urlpatterns)),
]
