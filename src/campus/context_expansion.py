"""Add one adjacent continuation when the highest-ranked fixed chunk ends mid-sentence."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from campus.chunking import TextChunk
from campus.retrieval import RetrievalHit


@dataclass(frozen=True, slots=True)
class ContextEvidence:
    chunk: TextChunk
    retrieval_rank: int | None
    cosine_score: float | None
    expanded_from_chunk_id: str | None = None


def _ends_at_sentence_boundary(text: str) -> bool:
    stripped = text.rstrip()
    return bool(stripped) and stripped[-1] in "。！？!?；;”’』」）》】"


def expand_top_hit_continuation(
    hits: Sequence[RetrievalHit],
    all_chunks: Sequence[TextChunk],
) -> tuple[list[ContextEvidence], list[dict[str, int | str]]]:
    """Keep retrieval ranks intact and add a same-document next chunk when needed."""
    if not hits:
        return [], []

    evidence = [
        ContextEvidence(hit.chunk, hit.rank, hit.score)
        for hit in hits
    ]
    anchor = hits[0].chunk
    chunk_index = anchor.metadata.get("chunk_index")
    char_count = anchor.metadata.get("char_count")
    if (
        not isinstance(chunk_index, int)
        or not isinstance(char_count, int)
        or char_count < 400
        or _ends_at_sentence_boundary(anchor.text)
    ):
        return evidence, []

    next_chunk = next(
        (
            chunk
            for chunk in all_chunks
            if chunk.source_id == anchor.source_id
            and chunk.metadata.get("chunk_index") == chunk_index + 1
        ),
        None,
    )
    if next_chunk is None:
        return evidence, []

    anchor_end = anchor.metadata.get("end_char")
    next_start = next_chunk.metadata.get("start_char")
    overlap_chars = (
        max(0, anchor_end - next_start)
        if isinstance(anchor_end, int) and isinstance(next_start, int)
        else 0
    )
    if (
        overlap_chars > 0
        and overlap_chars <= len(anchor.text)
        and overlap_chars <= len(next_chunk.text)
        and anchor.text[-overlap_chars:] == next_chunk.text[:overlap_chars]
    ):
        continuation = next_chunk.text[overlap_chars:].lstrip()
    else:
        overlap_chars = 0
        continuation = next_chunk.text
    if not continuation.strip():
        return evidence, []

    continuation_chunk = TextChunk(
        chunk_id=f"{next_chunk.chunk_id}:continuation:{anchor.chunk_id}",
        source_id=next_chunk.source_id,
        text=continuation,
        metadata={
            **next_chunk.metadata,
            "context_expansion": "adjacent_continuation",
            "expanded_from_chunk_id": anchor.chunk_id,
        },
    )
    evidence.insert(
        1,
        ContextEvidence(
            chunk=continuation_chunk,
            retrieval_rank=None,
            cosine_score=None,
            expanded_from_chunk_id=anchor.chunk_id,
        ),
    )
    return evidence, [
        {
            "source_id": anchor.source_id,
            "anchor_chunk_id": anchor.chunk_id,
            "continuation_chunk_id": next_chunk.chunk_id,
            "overlap_chars_removed": overlap_chars,
            "continuation_chars_added": len(continuation),
        }
    ]
