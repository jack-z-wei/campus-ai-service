"""Load the recorded campus vector index and synthetic SQLite tool service."""

from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path
from threading import Lock

import numpy as np

from campus.chunking import TextChunk
from campus.embeddings import OllamaBGEEmbeddings
from campus.knowledge import CampusKnowledgeSearch
from campus.tools.status import DEFAULT_DATABASE, CampusStatusTools

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INDEX_CONFIG = PROJECT_ROOT / "data" / "campus" / "index_config.json"
_CAMPUS_KNOWLEDGE_SEARCH: CampusKnowledgeSearch | None = None
_CAMPUS_KNOWLEDGE_SEARCH_INIT_LOCK = Lock()


def _project_path(relative_path: str) -> Path:
    path = (PROJECT_ROOT / relative_path).resolve()
    try:
        path.relative_to(PROJECT_ROOT.resolve())
    except ValueError as error:
        raise ValueError("Campus index path escapes the project root.") from error
    return path


def _load_campus_snapshot() -> tuple[dict, list[TextChunk], np.ndarray]:
    config = json.loads(INDEX_CONFIG.read_text(encoding="utf-8"))
    source_manifest = PROJECT_ROOT / "docs" / "campus" / "source_manifest.json"
    actual_hash = hashlib.sha256(source_manifest.read_bytes()).hexdigest()
    if config.get("source_manifest_sha256") != actual_hash:
        raise ValueError("Campus index is stale: source manifest hash has changed.")

    chunk_run = _project_path(f"runs/{config['chunk_run_id']}")
    chunks: list[TextChunk] = []
    with (chunk_run / "chunks.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            item = json.loads(line)
            chunks.append(
                TextChunk(
                    chunk_id=item["chunk_id"],
                    source_id=item["source_id"],
                    text=item["text"],
                    metadata=item["metadata"],
                )
            )
    vectors = np.load(chunk_run / "fixed_500_embeddings.npz")["vectors"]
    if len(chunks) != vectors.shape[0]:
        raise ValueError("Campus vector count does not match its recorded source chunks.")
    return config, chunks, vectors


def _build_campus_knowledge_search() -> CampusKnowledgeSearch:
    from campus.retrieval_chroma import ChromaVectorIndex

    config, chunks, vectors = _load_campus_snapshot()
    chroma_run = _project_path(f"runs/{config['chroma_run_id']}")
    index = ChromaVectorIndex(
        chroma_run / "chroma_db",
        config["chroma_collection"],
    )
    if index.collection.count() != len(chunks):
        raise ValueError("Campus vector index count does not match its recorded source chunks.")

    return CampusKnowledgeSearch(
        chunks,
        vectors,
        OllamaBGEEmbeddings(model=config["embedding"]["model"]),
        backend="chroma",
        chroma_index=index,
    )


def get_campus_knowledge_search() -> CampusKnowledgeSearch:
    """Initialize the shared Chroma client once, even on parallel first tool calls."""
    global _CAMPUS_KNOWLEDGE_SEARCH
    if _CAMPUS_KNOWLEDGE_SEARCH is not None:
        return _CAMPUS_KNOWLEDGE_SEARCH
    with _CAMPUS_KNOWLEDGE_SEARCH_INIT_LOCK:
        if _CAMPUS_KNOWLEDGE_SEARCH is None:
            _CAMPUS_KNOWLEDGE_SEARCH = _build_campus_knowledge_search()
        return _CAMPUS_KNOWLEDGE_SEARCH


@lru_cache(maxsize=1)
def get_principle_knowledge_search() -> CampusKnowledgeSearch:
    """Use the same frozen vector snapshot with the explicit NumPy cosine baseline."""
    config, chunks, vectors = _load_campus_snapshot()
    return CampusKnowledgeSearch(
        chunks,
        vectors,
        OllamaBGEEmbeddings(model=config["embedding"]["model"]),
        backend="numpy",
    )


@lru_cache(maxsize=1)
def get_campus_status_tools() -> CampusStatusTools:
    return CampusStatusTools(DEFAULT_DATABASE)
