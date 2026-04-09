from django.conf import settings
from django.db import models

from apps.app_server.models.base_model import BaseModel


class CourseEnrollment(BaseModel):
    SOURCE_DEMO_CHECKOUT = 'demo_checkout'
    SOURCE_ADMIN_GRANT = 'admin_grant'
    SOURCE_BULK_TEACHER_GRANT = 'bulk_teacher_grant'

    SOURCE_CHOICES = [
        (SOURCE_DEMO_CHECKOUT, 'Demo checkout'),
        (SOURCE_ADMIN_GRANT, 'Admin grant'),
        (SOURCE_BULK_TEACHER_GRANT, 'Bulk teacher grant'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='course_enrollments',
    )
    course = models.ForeignKey(
        'app_server.Course',
        on_delete=models.CASCADE,
        related_name='enrollments',
    )
    enrolled_at = models.DateTimeField(auto_now_add=True)
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='granted_course_enrollments',
    )
    source = models.CharField(
        max_length=32,
        choices=SOURCE_CHOICES,
        default=SOURCE_DEMO_CHECKOUT,
    )

    class Meta:
        db_table = 'course_enrollments'
        ordering = ['-enrolled_at']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'course'],
                name='unique_course_enrollment_per_user',
            ),
        ]

    def __str__(self):
        return f'{self.user_id}:{self.course_id}'
