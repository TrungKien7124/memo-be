from django.urls import path, include

urlpatterns = [
    path('', include('apps.app_server.routes.implemented.iam_route')),
    path('', include('apps.app_server.routes.implemented.cms_route')),
    path('', include('apps.app_server.routes.implemented.lms_route')),
]
