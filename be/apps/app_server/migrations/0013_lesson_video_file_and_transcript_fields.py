from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app_server', '0012_lessoncomment'),
    ]

    operations = [
        migrations.AddField(
            model_name='lesson',
            name='video_file',
            field=models.FileField(blank=True, null=True, upload_to='lessons/videos/'),
        ),
        migrations.AddField(
            model_name='lesson',
            name='transcript_error',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='lesson',
            name='transcript_language',
            field=models.CharField(blank=True, default='en', max_length=12),
        ),
        migrations.AddField(
            model_name='lesson',
            name='transcript_status',
            field=models.CharField(
                choices=[
                    ('not_started', 'Not started'),
                    ('processing', 'Processing'),
                    ('ready', 'Ready'),
                    ('failed', 'Failed'),
                ],
                default='not_started',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='lesson',
            name='transcript_text',
            field=models.TextField(blank=True, default=''),
        ),
    ]
