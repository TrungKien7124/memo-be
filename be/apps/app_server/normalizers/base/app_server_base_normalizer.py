from __future__ import annotations

import re


_whitespace_re = re.compile(r"\s+")


class CoreNormalizer:
    @staticmethod
    def normalize(value: str) -> str:
        return value


class LowercaseNormalizer(CoreNormalizer):
    @staticmethod
    def normalize(value: str) -> str:
        if value is None:
            return ""
        return _whitespace_re.sub(" ", value.strip()).lower()


class CoreInputNormalizer:
    def normalize(self, data):
        return data


class AppServerBaseInputNormalizer(CoreInputNormalizer):
    """Base input normalizer for app_server."""

    pass


def normalize_payload(data, normalizer_map):
    if not normalizer_map or data is None:
        return data
    if hasattr(data, "dict"):
        normalized = data.dict()
    elif isinstance(data, dict):
        normalized = dict(data)
    else:
        return data

    for field, normalizer in normalizer_map.items():
        if field in normalized and normalized[field] is not None:
            normalize = getattr(normalizer, "normalize", normalizer)
            normalized[field] = normalize(normalized[field])
    return normalized
