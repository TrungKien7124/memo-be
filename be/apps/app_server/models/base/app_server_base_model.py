from __future__ import annotations

from django.db import models


class AppServerBaseModel(models.Model):
    class Meta:
        abstract = True
