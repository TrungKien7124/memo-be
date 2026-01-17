from __future__ import annotations

from rest_framework.exceptions import ValidationError


class CoreValidator:
    @staticmethod
    def validate(value, _attrs=None) -> None:
        raise NotImplementedError


class RequiredValidator(CoreValidator):
    @staticmethod
    def validate(value, _attrs=None) -> None:
        if value in (None, "", []):
            raise ValidationError("This field is required.")


class MaxLengthValidator(CoreValidator):
    def __init__(self, max_length: int) -> None:
        self.max_length = max_length

    def validate(self, value, _attrs=None) -> None:
        if value is None:
            return
        if len(value) > self.max_length:
            raise ValidationError(f"Max length is {self.max_length}.")
