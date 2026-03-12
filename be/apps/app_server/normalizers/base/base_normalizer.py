class BaseNormalizer:
    """
    Normalize raw request data before it reaches the serializer.
    Subclasses override normalize() to apply transformations.
    """

    def __init__(self, data):
        self.data = data if isinstance(data, dict) else {}

    def normalize(self):
        return self.data

    @staticmethod
    def trim_strings(data):
        return {
            k: v.strip() if isinstance(v, str) else v
            for k, v in data.items()
        }

    @staticmethod
    def lowercase_field(data, field_name):
        if field_name in data and isinstance(data[field_name], str):
            data[field_name] = data[field_name].lower()
        return data
