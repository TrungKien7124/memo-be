from django.apps import AppConfig


class SrsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.srs'
    label = 'srs'
    verbose_name = 'Spaced Repetition System'
