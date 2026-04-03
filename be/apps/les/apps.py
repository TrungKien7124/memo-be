from django.apps import AppConfig


class LessonIngestionConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.les'
    label = 'lesson_ingestion'
    verbose_name = 'Lesson Ingestion'
