from __future__ import annotations

import pytest

from campus.chunking import (
    fixed_length_chunks,
    header_structure_chunks,
    recursive_boundary_chunks,
)
from campus.ingestion import CampusDocument, load_campus_documents


def test_loader_uses_manifest_allowlist_and_preserves_scope_metadata() -> None:
    documents = load_campus_documents()
    assert len(documents) == 14
    assert {document.metadata["category"] for document in documents} == {"教务", "奖助", "宿舍", "图书馆"}
    assert all(document.metadata["index_policy"] for document in documents)
    assert not any("student_management_2022.md" in document.metadata["source_file"] for document in documents)


def test_three_chunkers_are_document_local_and_within_configured_size() -> None:
    first = CampusDocument("source-a", "# 第一部分\n\n" + "甲乙丙。" * 260, {"category": "教务"})
    second = CampusDocument("source-b", "# 第二部分\n\n" + "丁戊己。" * 220, {"category": "宿舍"})

    chunkers = (
        lambda document: fixed_length_chunks(document, chunk_size=300, overlap=50),
        lambda document: recursive_boundary_chunks(document, chunk_size=300, overlap=50),
        lambda document: header_structure_chunks(document, chunk_size=300),
    )
    for chunker in chunkers:
        chunks = chunker(first) + chunker(second)
        assert chunks
        assert all(chunk.source_id in {"source-a", "source-b"} for chunk in chunks)
        assert all(len(chunk.text) <= 300 for chunk in chunks)
        assert len({chunk.chunk_id for chunk in chunks}) == len(chunks)
        assert {chunk.metadata["source_id"] for chunk in chunks} == {"source-a", "source-b"}

    structured = header_structure_chunks(first, chunk_size=300)
    assert all(chunk.metadata.get("header_path") == "第一部分" for chunk in structured)


@pytest.mark.parametrize(
    ("chunk_size", "overlap"),
    [(0, 0), (10, 10), (10, 11), (-1, 0)],
)
def test_fixed_and_recursive_chunkers_reject_invalid_ranges(chunk_size: int, overlap: int) -> None:
    document = CampusDocument("source", "内容", {})
    with pytest.raises(ValueError):
        fixed_length_chunks(document, chunk_size=chunk_size, overlap=overlap)
    with pytest.raises(ValueError):
        recursive_boundary_chunks(document, chunk_size=chunk_size, overlap=overlap)

