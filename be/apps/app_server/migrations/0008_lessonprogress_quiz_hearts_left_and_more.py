from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app_server', '0007_lessonprogress_quiz_attempts_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='lessonprogress',
            name='quiz_correct_count',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='lessonprogress',
            name='quiz_current_question_index',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='lessonprogress',
            name='quiz_hearts_left',
            field=models.PositiveIntegerField(default=5),
        ),
    ]
