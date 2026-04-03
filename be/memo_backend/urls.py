from django.contrib import admin
from django.urls import path, include

from apps.app_server.controllers.implemented.health_controller import HealthCheckView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/', HealthCheckView.as_view(), name='health-check'),
    path('api/', include('apps.app_server.routes')),
    path('api/', include('apps.les.routes')),
    path('api/', include('apps.srs.routes')),
    path('api/', include('apps.ai.routes')),
]
