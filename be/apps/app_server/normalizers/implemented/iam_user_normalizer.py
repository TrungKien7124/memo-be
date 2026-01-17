from __future__ import annotations

from apps.app_server.normalizers.base.app_server_base_normalizer import (
    AppServerBaseInputNormalizer,
    LowercaseNormalizer,
    normalize_payload,
)


class UserInputNormalizer(AppServerBaseInputNormalizer):
    def normalize(self, data):
        return normalize_payload(data, {"email": LowercaseNormalizer})
