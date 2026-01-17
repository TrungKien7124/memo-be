from __future__ import annotations

from django.core.exceptions import ImproperlyConfigured
from rest_framework import viewsets

from apps.app_server.normalizers.base.app_server_base_normalizer import normalize_payload


class CoreModelViewSet(viewsets.ModelViewSet):
    model = None
    input_normalizer_class = None
    input_normalizer_map = None

    def get_queryset(self):
        if self.queryset is not None:
            return super().get_queryset()
        if self.model is None:
            raise ImproperlyConfigured("CoreModelViewSet requires 'model' or 'queryset'.")
        return self.model.objects.all()

    def normalize_input(self, data):
        if data is None:
            return data
        if self.input_normalizer_class is not None:
            normalizer = self.input_normalizer_class()
            return normalizer.normalize(data)
        if self.input_normalizer_map:
            return normalize_payload(data, self.input_normalizer_map)
        return data

    def get_serializer(self, *args, **kwargs):
        if "data" in kwargs:
            kwargs["data"] = self.normalize_input(kwargs.get("data"))
        return super().get_serializer(*args, **kwargs)
