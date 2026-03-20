# Generated manually for lesson-scoped chat binding

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ai', '0001_initial'),
        ('app_server', '0008_lessonprogress_quiz_hearts_left_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='conversation',
            name='lesson',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='ai_conversations',
                to='app_server.lesson',
            ),
        ),
    ]
