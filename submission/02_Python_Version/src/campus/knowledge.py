"""Campus RAG search over the frozen local vector snapshot."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np

from campus.chunking import TextChunk
from campus.embeddings import OllamaBGEEmbeddings
from campus.retrieval import RetrievalHit, cosine_search
from campus.retrieval_chroma import ChromaVectorIndex


CURRENT_QUERY_EXCLUDED_POLICIES = {"archive_not_for_current_answers"}


@dataclass(frozen=True, slots=True)
class KnowledgeSearchResult:
    hits: list[RetrievalHit]
    backend: str


class CampusKnowledgeSearch:
    def __init__(
        self,
        chunks: Sequence[TextChunk],
        vectors: Sequence[Sequence[float]] | np.ndarray,
        embedder: OllamaBGEEmbeddings,
        *,
        backend: str = "numpy",
        chroma_index: ChromaVectorIndex | None = None,
    ) -> None:
        self.chunks = list(chunks)
        self.vectors = np.asarray(vectors, dtype=np.float32)
        self.embedder = embedder
        self.backend = backend
        self.chroma_index = chroma_index
        if len(self.chunks) != self.vectors.shape[0]:
            raise ValueError("Campus chunks and vectors must have matching counts.")
        if backend not in {"numpy", "chroma"}:
            raise ValueError("backend must be numpy or chroma.")
        if backend == "chroma" and chroma_index is None:
            raise ValueError("A Chroma index is required for the Chroma backend.")

    def search(self, query: str, *, top_k: int = 5) -> KnowledgeSearchResult:
        if not query.strip():
            raise ValueError("Search query cannot be empty.")
        query_vector = self.embedder.embed_query(query)
        if self.backend == "chroma":
            hits = self.chroma_index.search(
                query_vector,
                top_k=top_k,
                exclude_index_policies=CURRENT_QUERY_EXCLUDED_POLICIES,
            )
        else:
            hits = cosine_search(
                query_vector,
                self.chunks,
                self.vectors,
                top_k=top_k,
                exclude_index_policies=CURRENT_QUERY_EXCLUDED_POLICIES,
            )
        return KnowledgeSearchResult(hits=hits, backend=self.backend)

