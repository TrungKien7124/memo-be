import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models

from apps.app_server.models.base.base_model import SoftDeleteManager


ROLE_STUDENT = 'student'
ROLE_TEACHER = 'teacher'
ROLE_ADMIN = 'admin'

ROLE_CHOICES = [
    (ROLE_STUDENT, 'Student'),
    (ROLE_TEACHER, 'Teacher'),
    (ROLE_ADMIN, 'Admin'),
]


class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=ROLE_STUDENT)
    is_deleted = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    objects = SoftDeleteManager()

    class Meta:
        db_table = 'users'
        ordering = ['-created_at']

    def __str__(self):
        return self.email

    def soft_delete(self):
        self.is_deleted = True
        self.is_active = False
        self.save(update_fields=['is_deleted', 'is_active', 'updated_at'])

    def restore(self):
        self.is_deleted = False
        self.is_active = True
        self.save(update_fields=['is_deleted', 'is_active', 'updated_at'])
