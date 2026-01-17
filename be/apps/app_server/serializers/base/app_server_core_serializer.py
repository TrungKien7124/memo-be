from __future__ import annotations

from rest_framework import serializers
from rest_framework.exceptions import ValidationError


class CoreModelSerializer(serializers.ModelSerializer):
    field_list = None
    ignore_fields = ()
    validation_rules = {}
    output_fields = None
    output_formatters = {}

    class Meta:
        model = None
        fields = "__all__"

    def get_fields(self):
        fields = super().get_fields()
        if self.field_list:
            fields = {name: fields[name] for name in self.field_list if name in fields}
        if self.ignore_fields:
            for name in self.ignore_fields:
                fields.pop(name, None)
        return fields

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if self.output_fields:
            data = {name: data[name] for name in self.output_fields if name in data}
        if self.output_formatters:
            for field, formatter in self.output_formatters.items():
                if field in data:
                    format_value = getattr(formatter, "format", formatter)
                    data[field] = format_value(data[field], data)
        return data

    def validate(self, attrs):
        errors = {}
        for field, rules in self.validation_rules.items():
            if not isinstance(rules, (list, tuple)):
                rules = [rules]
            for rule in rules:
                validate = getattr(rule, "validate", rule)
                try:
                    validate(attrs.get(field), attrs)
                except ValidationError as exc:
                    errors.setdefault(field, []).extend(exc.detail if hasattr(exc, "detail") else [str(exc)])
        if errors:
            raise ValidationError(errors)
        return attrs
