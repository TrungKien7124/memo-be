from django.urls import path, include

urlpatterns = [
    path('', include('apps.app_server.routes.implemented.iam_route')),
]
