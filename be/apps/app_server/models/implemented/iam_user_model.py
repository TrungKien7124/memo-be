from __future__ import annotations

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=50, blank=True)

    class Meta:
        db_table = "users"

    def __str__(self) -> str:
        return self.email or self.username
