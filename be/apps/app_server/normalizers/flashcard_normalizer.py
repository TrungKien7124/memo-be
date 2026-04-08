from apps.app_server.normalizers.base_normalizer import BaseNormalizer


class FlashcardNormalizer(BaseNormalizer):
    def normalize(self):
        data = self.trim_strings(self.data)
        return data
