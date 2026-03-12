from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('apps.app_server.routes')),
    path('api/', include('apps.srs.routes')),
    path('api/', include('apps.ai.routes')),
]
