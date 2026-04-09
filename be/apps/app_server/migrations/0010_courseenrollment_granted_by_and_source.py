import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app_server', '0009_courseenrollment'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='courseenrollment',
            name='granted_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='granted_course_enrollments',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='courseenrollment',
            name='source',
            field=models.CharField(
                choices=[
                    ('demo_checkout', 'Demo checkout'),
                    ('admin_grant', 'Admin grant'),
                    ('bulk_teacher_grant', 'Bulk teacher grant'),
                ],
                default='demo_checkout',
                max_length=32,
            ),
        ),
    ]
