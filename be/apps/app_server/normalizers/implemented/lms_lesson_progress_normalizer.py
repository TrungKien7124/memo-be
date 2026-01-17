from __future__ import annotations

from apps.app_server.normalizers.base.app_server_base_normalizer import AppServerBaseInputNormalizer


class LessonProgressInputNormalizer(AppServerBaseInputNormalizer):
    def normalize(self, data):
        return data
