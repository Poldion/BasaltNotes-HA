"""Text embeddings from an OpenAI-compatible server (Ollama, OpenAI, …), to pick notes by meaning."""

from __future__ import annotations

import math

import aiohttp

REQUEST_TIMEOUT = 20


class EmbeddingError(Exception):
    """The embedding server did not deliver."""


def cosine(a: list[float], b: list[float]) -> float:
    """Return the cosine similarity of two vectors."""
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return dot / norm if norm else 0.0


class Embedder:
    """Turn texts into vectors."""

    def __init__(
        self, session: aiohttp.ClientSession, url: str, model: str, api_key: str | None = None
    ) -> None:
        """Initialize the embedder; url is the base of the API, e.g. http://nas.local:11434/v1."""
        self._session = session
        self._url = f"{url.rstrip('/')}/embeddings"
        self.model = model
        self._api_key = api_key

    def _prefix(self, query: bool) -> str:
        # EmbeddingGemma was trained with these prefixes and separates matches clearly better with them
        if "embeddinggemma" not in self.model:
            return ""
        return "task: search result | query: " if query else "title: none | text: "

    async def async_embed(self, texts: list[str], *, query: bool) -> list[list[float]]:
        """Return one vector per text."""
        headers = {"Authorization": f"Bearer {self._api_key}"} if self._api_key else {}
        prefix = self._prefix(query)
        try:
            async with self._session.post(
                self._url,
                json={"model": self.model, "input": [prefix + text for text in texts]},
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
            ) as response:
                if response.status >= 400:
                    raise EmbeddingError(f"HTTP {response.status}: {await response.text()}")
                data = await response.json(content_type=None)
        except (TimeoutError, aiohttp.ClientError) as err:
            raise EmbeddingError(str(err)) from err
        try:
            vectors = [
                item["embedding"] for item in sorted(data["data"], key=lambda item: item.get("index", 0))
            ]
        except (KeyError, TypeError) as err:
            raise EmbeddingError(f"Unexpected answer: {str(data)[:200]}") from err
        if len(vectors) != len(texts):
            raise EmbeddingError(f"Expected {len(texts)} vectors, got {len(vectors)}")
        return vectors
