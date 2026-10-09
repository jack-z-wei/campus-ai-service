from __future__ import annotations

import pytest

from campus.chunking import TextChunk
from campus.retrieval import cosine_search


def chunk(chunk_id: str) -> TextChunk:
    return TextChunk(chunk_id=chunk_id, source_id=chunk_id, text=chunk_id, metadata={})


def test_cosine_search_orders_by_similarity_and_returns_real_chunks() -> None:
    chunks = [chunk("parallel"), chunk("opposite"), chunk("diagonal")]
    hits = cosine_search([1, 0], chunks, [[1, 0], [-1, 0], [1, 1]], top_k=3)
    assert [hit.chunk.chunk_id for hit in hits] == ["parallel", "diagonal", "opposite"]
    assert [hit.rank for hit in hits] == [1, 2, 3]
    assert hits[0].score == pytest.approx(1.0)
    assert hits[1].score == pytest.approx(2**-0.5)


def test_cosine_search_rejects_dimension_mismatch_and_zero_vectors() -> None:
    with pytest.raises(ValueError, match="compatible dimensions"):
        cosine_search([1, 0], [chunk("x")], [[1, 0, 0]])
    with pytest.raises(ValueError, match="zero vectors"):
        cosine_search([0, 0], [chunk("x")], [[1, 0]])


def test_cosine_search_can_exclude_archived_policy_chunks() -> None:
    archive = TextChunk("archive", "archive", "old hours", {"index_policy": "archive_not_for_current_answers"})
    current = TextChunk("current", "current", "current homepage", {"index_policy": "current_homepage_snapshot"})
    hits = cosine_search(
        [1, 0],
        [archive, current],
        [[1, 0], [0.9, 0.1]],
        exclude_index_policies={"archive_not_for_current_answers"},
    )
    assert [hit.chunk.chunk_id for hit in hits] == ["current"]


def test_chroma_index_persists_and_filters_by_source_policy(tmp_path) -> None:
    chromadb = pytest.importorskip("chromadb")
    from campus.retrieval_chroma import ChromaVectorIndex

    index = ChromaVectorIndex(tmp_path / "chroma", collection_name="campus-test-v1")
    index.add_chunks(
        [
            TextChunk("archive", "archive", "old hours", {"index_policy": "archive_not_for_current_answers"}),
            TextChunk("current", "current", "current homepage", {"index_policy": "current_homepage_snapshot"}),
        ],
        [[1, 0], [0.9, 0.1]],
    )
    hits = index.search(
        [1, 0],
        top_k=2,
        exclude_index_policies={"archive_not_for_current_answers"},
    )
    assert hits[0].chunk.chunk_id == "current"

