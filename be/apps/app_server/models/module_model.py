from django.db import models

from apps.app_server.models.base_model import BaseModel


class Module(BaseModel):
    course = models.ForeignKey(
        'app_server.Course',
        on_delete=models.CASCADE,
        related_name='modules',
    )
    title = models.CharField(max_length=255)
    order_index = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'modules'
        ordering = ['order_index']

    def __str__(self):
        return f'{self.course.title} - {self.title}'
