from rest_framework import serializers


class CoreModelSerializer(serializers.ModelSerializer):
    """
    Base serializer with field_list / ignore_fields support.
    Subclasses can define:
        field_list   – explicit list of fields to expose
        ignore_fields – fields to exclude from output
    """

    field_list = None
    ignore_fields = None

    def get_fields(self):
        fields = super().get_fields()

        if self.field_list is not None:
            allowed = set(self.field_list)
            fields = {k: v for k, v in fields.items() if k in allowed}

        if self.ignore_fields is not None:
            for field_name in self.ignore_fields:
                fields.pop(field_name, None)

        return fields

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if hasattr(instance, 'is_deleted'):
            data.pop('is_deleted', None)
        return data
