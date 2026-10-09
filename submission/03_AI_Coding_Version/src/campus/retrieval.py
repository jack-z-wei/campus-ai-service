"""Small, auditable cosine-similarity retrieval baseline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np

from campus.chunking import TextChunk


@dataclass(frozen=True, slots=True)
class RetrievalHit:
    rank: int
    score: float
    chunk: TextChunk


def cosine_search(
    query_vector: Sequence[float],
    chunks: Sequence[TextChunk],
    vectors: Sequence[Sequence[float]] | np.ndarray,
    *,
    top_k: int = 5,
    exclude_index_policies: set[str] | None = None,
) -> list[RetrievalHit]:
    if top_k < 1:
        raise ValueError("top_k must be positive.")
    if len(chunks) != len(vectors):
        raise ValueError("Chunk and vector counts must match.")
    if not chunks:
        return []

    matrix = np.asarray(vectors, dtype=np.float64)
    query = np.asarray(query_vector, dtype=np.float64)
    if matrix.ndim != 2 or query.ndim != 1 or matrix.shape[1] != query.shape[0]:
        raise ValueError("Query and document vectors must have compatible dimensions.")
    if not np.isfinite(matrix).all() or not np.isfinite(query).all():
        raise ValueError("Vectors must contain only finite values.")
    norms = np.linalg.norm(matrix, axis=1)
    query_norm = float(np.linalg.norm(query))
    if query_norm == 0 or np.any(norms == 0):
        raise ValueError("Cosine similarity is undefined for zero vectors.")
    scores = (matrix @ query) / (norms * query_norm)
    excluded = exclude_index_policies or set()
    eligible = [
        index
        for index, chunk in enumerate(chunks)
        if chunk.metadata.get("index_policy") not in excluded
    ]
    ordered = sorted(
        eligible,
        key=lambda index: (-float(scores[index]), chunks[index].chunk_id),
    )[: min(top_k, len(eligible))]
    return [
        RetrievalHit(rank=rank, score=float(scores[index]), chunk=chunks[index])
        for rank, index in enumerate(ordered, start=1)
    ]

