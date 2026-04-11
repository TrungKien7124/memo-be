from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app_server', '0013_lesson_video_file_and_transcript_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='lesson',
            name='is_active',
            field=models.BooleanField(
                default=True,
                help_text='When false, learners do not see this lesson until publication pipeline completes.',
            ),
        ),
        migrations.AddField(
            model_name='lesson',
            name='publication_status',
            field=models.CharField(
                choices=[
                    ('draft', 'Draft'),
                    ('processing', 'Processing'),
                    ('ready', 'Ready'),
                    ('failed', 'Failed'),
                ],
                default='ready',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='lesson',
            name='publication_error',
            field=models.TextField(blank=True, default=''),
        ),
    ]
