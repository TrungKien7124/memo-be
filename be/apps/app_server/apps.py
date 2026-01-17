from __future__ import annotations

from django.apps import AppConfig


class AppServerConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.app_server"
    verbose_name = "App Server"
