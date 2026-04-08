import uuid

from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models

from apps.app_server.models.base_model import SoftDeleteQuerySet


ROLE_STUDENT = 'student'
ROLE_TEACHER = 'teacher'
ROLE_ADMIN = 'admin'

ROLE_CHOICES = [
    (ROLE_STUDENT, 'Student'),
    (ROLE_TEACHER, 'Teacher'),
    (ROLE_ADMIN, 'Admin'),
]


class SoftDeleteUserManager(UserManager):
    """UserManager that filters out soft-deleted users by default."""

    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db).alive()

    def all_with_deleted(self):
        return SoftDeleteQuerySet(self.model, using=self._db)

    def deleted_only(self):
        return SoftDeleteQuerySet(self.model, using=self._db).dead()


class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=ROLE_STUDENT)
    is_deleted = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    objects = SoftDeleteUserManager()

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
