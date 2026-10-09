"""Persistent Chroma adapter for the campus engineering retrieval track."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

import chromadb
import numpy as np
from chromadb.config import Settings

from campus.chunking import TextChunk
from campus.retrieval import RetrievalHit


def _chroma_metadata(chunk: TextChunk) -> dict[str, str | int | float | bool]:
    return {
        key: value
        for key, value in chunk.metadata.items()
        if isinstance(value, (str, int, float, bool))
    }


class ChromaVectorIndex:
    def __init__(self, persist_directory: Path, collection_name: str) -> None:
        if not collection_name or len(collection_name) < 3 or len(collection_name) > 63:
            raise ValueError("Chroma collection name must be between 3 and 63 characters.")
        persist_directory.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(
            path=str(persist_directory),
            settings=Settings(anonymized_telemetry=False),
        )
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def add_chunks(
        self,
        chunks: Sequence[TextChunk],
        vectors: Sequence[Sequence[float]] | np.ndarray,
    ) -> None:
        if not chunks:
            raise ValueError("Cannot create a Chroma index without chunks.")
        matrix = np.asarray(vectors, dtype=np.float32)
        if matrix.ndim != 2 or matrix.shape[0] != len(chunks):
            raise ValueError("Chunk and vector counts must match.")
        if not np.isfinite(matrix).all():
            raise ValueError("Chroma vectors must contain only finite values.")
        self.collection.add(
            ids=[chunk.chunk_id for chunk in chunks],
            embeddings=matrix.tolist(),
            documents=[chunk.text for chunk in chunks],
            metadatas=[_chroma_metadata(chunk) for chunk in chunks],
        )

    def search(
        self,
        query_vector: Sequence[float],
        *,
        top_k: int = 5,
        exclude_index_policies: set[str] | None = None,
    ) -> list[RetrievalHit]:
        if top_k < 1:
            raise ValueError("top_k must be positive.")
        query = np.asarray(query_vector, dtype=np.float32)
        if query.ndim != 1 or not np.isfinite(query).all() or np.linalg.norm(query) == 0:
            raise ValueError("Query vector must be a finite non-zero vector.")
        excluded = sorted(exclude_index_policies or set())
        where = None
        if len(excluded) == 1:
            where = {"index_policy": {"$ne": excluded[0]}}
        elif excluded:
            where = {"$and": [{"index_policy": {"$ne": policy}} for policy in excluded]}

        result = self.collection.query(
            query_embeddings=[query.tolist()],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        ids = result.get("ids", [[]])[0]
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]
        hits: list[RetrievalHit] = []
        for rank, (chunk_id, text, metadata, distance) in enumerate(
            zip(ids, documents, metadatas, distances, strict=True), start=1
        ):
            source_id = str(metadata.get("source_id", "unknown"))
            chunk = TextChunk(
                chunk_id=chunk_id,
                source_id=source_id,
                text=text,
                metadata=dict(metadata),
            )
            hits.append(RetrievalHit(rank=rank, score=1.0 - float(distance), chunk=chunk))
        return hits

