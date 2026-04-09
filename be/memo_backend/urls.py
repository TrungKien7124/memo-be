from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from apps.app_server.controllers.health_controller import HealthCheckView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/', HealthCheckView.as_view(), name='health-check'),
    path('api/', include('apps.app_server.routes')),
    path('api/', include('apps.les.routes')),
    path('api/', include('apps.srs.routes')),
    path('api/', include('apps.ai.routes')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
