"""Local Ollama BGE-M3 embeddings with bounded batches and no automatic retry."""

from __future__ import annotations

import math
from dataclasses import dataclass

import httpx


@dataclass(frozen=True, slots=True)
class EmbeddingBatchResult:
    vectors: list[list[float]]
    model: str
    dimension: int
    batches_completed: int


class OllamaBGEEmbeddings:
    def __init__(
        self,
        *,
        base_url: str = "http://127.0.0.1:11434",
        model: str = "bge-m3:latest",
        batch_size: int = 8,
        timeout_seconds: float = 90.0,
    ) -> None:
        if batch_size < 1:
            raise ValueError("batch_size must be positive.")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive.")
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.batch_size = batch_size
        self.timeout_seconds = timeout_seconds

    def embed_documents(self, texts: list[str]) -> EmbeddingBatchResult:
        if not texts:
            raise ValueError("At least one document text is required.")
        if any(not isinstance(text, str) or not text.strip() for text in texts):
            raise ValueError("Embedding inputs must be non-empty strings.")

        vectors: list[list[float]] = []
        dimension: int | None = None
        batches_completed = 0
        with httpx.Client(timeout=self.timeout_seconds, trust_env=False) as client:
            for start in range(0, len(texts), self.batch_size):
                batch = texts[start : start + self.batch_size]
                response = client.post(
                    f"{self.base_url}/api/embed",
                    json={"model": self.model, "input": batch, "truncate": False},
                )
                response.raise_for_status()
                payload = response.json()
                batch_vectors = payload.get("embeddings")
                if not isinstance(batch_vectors, list) or len(batch_vectors) != len(batch):
                    raise ValueError("Ollama returned a vector count that does not match the batch.")
                for vector in batch_vectors:
                    if not isinstance(vector, list) or not vector:
                        raise ValueError("Ollama returned an empty or invalid embedding vector.")
                    if any(not isinstance(value, (int, float)) or not math.isfinite(value) for value in vector):
                        raise ValueError("Ollama returned non-finite embedding values.")
                    if dimension is None:
                        dimension = len(vector)
                    elif dimension != len(vector):
                        raise ValueError("Ollama returned inconsistent embedding dimensions.")
                    vectors.append([float(value) for value in vector])
                batches_completed += 1

        if dimension is None:
            raise ValueError("Ollama returned no embeddings.")
        return EmbeddingBatchResult(
            vectors=vectors,
            model=self.model,
            dimension=dimension,
            batches_completed=batches_completed,
        )

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text]).vectors[0]

