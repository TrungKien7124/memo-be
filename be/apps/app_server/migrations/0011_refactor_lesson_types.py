from django.db import migrations, models


def migrate_legacy_lesson_types(apps, schema_editor):
    lesson_model = apps.get_model('app_server', 'Lesson')
    lesson_model.objects.filter(lesson_type__in=['video', 'text']).update(lesson_type='lesson')


def noop_reverse(apps, schema_editor):
    # Keep forward-only mapping to avoid lossy reverse conversion.
    return


class Migration(migrations.Migration):

    dependencies = [
        ('app_server', '0010_courseenrollment_granted_by_and_source'),
    ]

    operations = [
        migrations.RunPython(migrate_legacy_lesson_types, reverse_code=noop_reverse),
        migrations.AlterField(
            model_name='lesson',
            name='lesson_type',
            field=models.CharField(
                choices=[('lesson', 'Lesson'), ('quiz', 'Quiz')],
                default='lesson',
                max_length=10,
            ),
        ),
    ]
