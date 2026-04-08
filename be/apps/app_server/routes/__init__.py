from django.urls import path, include

urlpatterns = [
    path('', include('apps.app_server.routes.auth_route')),
    path('', include('apps.app_server.routes.course_route')),
    path('', include('apps.app_server.routes.module_route')),
    path('', include('apps.app_server.routes.lesson_route')),
    path('', include('apps.app_server.routes.lesson_progress_route')),
    path('', include('apps.app_server.routes.flashcard_route')),
    path('', include('apps.app_server.routes.xp_route')),
]
