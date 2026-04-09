"""
Gemini embedding client for lesson RAG (index + query only; no generation here).
"""

from __future__ import annotations

import logging
import os
from typing import Sequence

from django.conf import settings

logger = logging.getLogger(__name__)


def resolve_gemini_api_key() -> str:
    return (
        (os.getenv('GEMINI_API_KEY') or '').strip()
        or (os.getenv('GOOGLE_API_KEY') or '').strip()
        or (getattr(settings, 'GEMINI_API_KEY', None) or '').strip()
        or (getattr(settings, 'GOOGLE_AI_API_KEY', None) or '').strip()
    )


def _embedding_values(embedding_obj) -> list[float]:
    if embedding_obj is None:
        return []
    if hasattr(embedding_obj, 'values'):
        return [float(x) for x in embedding_obj.values]
    if isinstance(embedding_obj, (list, tuple)):
        return [float(x) for x in embedding_obj]
    return []


class GeminiEmbeddingClient:
    """
    Wraps the Google GenAI SDK for ``gemini-embedding-001`` with fixed output size.
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        output_dimensionality: int | None = None,
        timeout_seconds: float | None = None,
    ):
        self.api_key = api_key if api_key is not None else resolve_gemini_api_key()
        self.model = model or getattr(settings, 'AI_GEMINI_EMBED_MODEL', 'gemini-embedding-001')
        self.output_dimensionality = int(
            output_dimensionality
            if output_dimensionality is not None
            else getattr(settings, 'AI_GEMINI_EMBED_DIMENSIONS', 768)
        )
        timeout = timeout_seconds
        if timeout is None:
            timeout = float(getattr(settings, 'AI_GEMINI_EMBED_TIMEOUT', '60') or 60)
        self.timeout_seconds = timeout
        self._client = None

    def _get_client(self):
        if self._client is not None:
            return self._client
        if not self.api_key:
            raise RuntimeError(
                'Gemini API key missing. Set GEMINI_API_KEY, GOOGLE_API_KEY, or GOOGLE_AI_API_KEY.'
            )
        try:
            from google import genai
            from google.genai import types as genai_types
        except ImportError as exc:
            raise RuntimeError(
                'google-genai is not installed. Add google-genai to requirements.txt'
            ) from exc
        timeout_ms = max(1, int(round(float(self.timeout_seconds) * 1000)))
        self._client = genai.Client(
            api_key=self.api_key,
            http_options=genai_types.HttpOptions(timeout=timeout_ms),
        )
        return self._client

    def embed_documents(
        self,
        documents: Sequence[str],
        *,
        title_prefix: str | None = None,
    ) -> list[list[float]]:
        if not documents:
            return []
        from google.genai import types

        client = self._get_client()
        batch_size = max(1, int(getattr(settings, 'AI_GEMINI_EMBED_BATCH_SIZE', '16') or 16))
        out: list[list[float]] = []
        for start in range(0, len(documents), batch_size):
            batch = list(documents[start : start + batch_size])
            if title_prefix is not None:
                for i, text in enumerate(batch):
                    global_idx = start + i
                    title = f'{title_prefix} chunk {global_idx}'
                    result = client.models.embed_content(
                        model=self.model,
                        contents=text,
                        config=types.EmbedContentConfig(
                            output_dimensionality=self.output_dimensionality,
                            task_type='RETRIEVAL_DOCUMENT',
                            title=title,
                        ),
                    )
                    vec = _embedding_values(result.embeddings[0] if result.embeddings else None)
                    self._assert_dim(vec)
                    out.append(vec)
            else:
                result = client.models.embed_content(
                    model=self.model,
                    contents=batch,
                    config=types.EmbedContentConfig(
                        output_dimensionality=self.output_dimensionality,
                        task_type='RETRIEVAL_DOCUMENT',
                    ),
                )
                if not result.embeddings or len(result.embeddings) != len(batch):
                    raise RuntimeError('Gemini batch embed returned unexpected embedding count.')
                for emb in result.embeddings:
                    vec = _embedding_values(emb)
                    self._assert_dim(vec)
                    out.append(vec)
        return out

    def embed_query(self, query: str) -> list[float]:
        from google.genai import types

        client = self._get_client()
        result = client.models.embed_content(
            model=self.model,
            contents=query,
            config=types.EmbedContentConfig(
                output_dimensionality=self.output_dimensionality,
                task_type='RETRIEVAL_QUERY',
            ),
        )
        vec = _embedding_values(result.embeddings[0] if result.embeddings else None)
        self._assert_dim(vec)
        return vec

    def _assert_dim(self, vec: list[float]) -> None:
        if len(vec) != self.output_dimensionality:
            raise RuntimeError(
                f'Expected embedding length {self.output_dimensionality}, got {len(vec)}'
            )


_gemini_client_singleton: GeminiEmbeddingClient | None = None


def get_gemini_embedding_client() -> GeminiEmbeddingClient:
    global _gemini_client_singleton
    if _gemini_client_singleton is None:
        _gemini_client_singleton = GeminiEmbeddingClient()
    return _gemini_client_singleton


def reset_gemini_embedding_client_for_tests() -> None:
    global _gemini_client_singleton
    _gemini_client_singleton = None
