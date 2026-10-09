"""Deterministic per-document chunkers for the campus source corpus."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Iterable

from campus.ingestion import CampusDocument


@dataclass(frozen=True, slots=True)
class TextChunk:
    chunk_id: str
    source_id: str
    text: str
    metadata: dict[str, object]


def _chunk_id(source_id: str, strategy: str, config: str, index: int, text: str) -> str:
    stable = f"{source_id}\0{strategy}\0{config}\0{index}\0{text}".encode("utf-8")
    return hashlib.sha256(stable).hexdigest()[:24]


def _to_chunks(
    document: CampusDocument,
    pieces: Iterable[tuple[str, int, int, str | None]],
    *,
    strategy: str,
    config: str,
) -> list[TextChunk]:
    chunks: list[TextChunk] = []
    for index, (text, start, end, header_path) in enumerate(pieces):
        cleaned = text.strip()
        if not cleaned:
            continue
        metadata = {
            **document.metadata,
            "source_id": document.source_id,
            "chunk_index": index,
            "strategy": strategy,
            "start_char": start,
            "end_char": end,
            "char_count": len(cleaned),
        }
        if header_path:
            metadata["header_path"] = header_path
        chunks.append(
            TextChunk(
                chunk_id=_chunk_id(document.source_id, strategy, config, index, cleaned),
                source_id=document.source_id,
                text=cleaned,
                metadata=metadata,
            )
        )
    return chunks


def fixed_length_chunks(
    document: CampusDocument,
    *,
    chunk_size: int = 500,
    overlap: int = 80,
) -> list[TextChunk]:
    if chunk_size < 1 or overlap < 0 or overlap >= chunk_size:
        raise ValueError("Require chunk_size > overlap >= 0.")
    text = document.text
    stride = chunk_size - overlap
    pieces = (
        (text[start : start + chunk_size], start, min(start + chunk_size, len(text)), None)
        for start in range(0, len(text), stride)
    )
    return _to_chunks(
        document,
        pieces,
        strategy="fixed_length",
        config=f"size={chunk_size};overlap={overlap}",
    )


def _split_preserving_separator(text: str, separator: str) -> list[str]:
    parts = text.split(separator)
    result: list[str] = []
    for index, part in enumerate(parts):
        if index < len(parts) - 1:
            part += separator
        if part:
            result.append(part)
    return result


def _recursive_pieces(text: str, size: int, separators: tuple[str, ...]) -> list[str]:
    if len(text) <= size:
        return [text]
    for index, separator in enumerate(separators):
        if separator in text:
            groups: list[str] = []
            current = ""
            for piece in _split_preserving_separator(text, separator):
                if len(piece) > size:
                    if current:
                        groups.append(current)
                        current = ""
                    groups.extend(_recursive_pieces(piece, size, separators[index + 1 :]))
                    continue
                if current and len(current) + len(piece) > size:
                    groups.append(current)
                    current = piece
                else:
                    current += piece
            if current:
                groups.append(current)
            return groups
    return [text[start : start + size] for start in range(0, len(text), size)]


def recursive_boundary_chunks(
    document: CampusDocument,
    *,
    chunk_size: int = 500,
    overlap: int = 80,
) -> list[TextChunk]:
    if chunk_size < 1 or overlap < 0 or overlap >= chunk_size:
        raise ValueError("Require chunk_size > overlap >= 0.")
    separators = ("\n\n", "\n", "。", "！", "？", "；", "，", " ")
    base = _recursive_pieces(document.text, chunk_size - overlap, separators)
    pieces: list[tuple[str, int, int, str | None]] = []
    search_from = 0
    previous = ""
    for index, part in enumerate(base):
        start = document.text.find(part, search_from)
        if start < 0:
            start = search_from
        end = start + len(part)
        prefix = ""
        if index and overlap:
            prefix = previous[-overlap:]
        combined = prefix + part
        pieces.append((combined, max(0, start - len(prefix)), end, None))
        search_from = end
        previous = part
    return _to_chunks(
        document,
        pieces,
        strategy="recursive_boundary",
        config=f"size={chunk_size};overlap={overlap}",
    )


def _section_chunks(document: CampusDocument, chunk_size: int) -> list[tuple[str, int, int, str | None]]:
    heading_pattern = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
    matches = list(heading_pattern.finditer(document.text))
    if not matches:
        return [
            (part, start, min(start + len(part), len(document.text)), None)
            for start, part in _offset_recursive_pieces(document.text, chunk_size)
        ]

    output: list[tuple[str, int, int, str | None]] = []
    stack: list[tuple[int, str]] = []
    preamble_end = matches[0].start()
    preamble = document.text[:preamble_end]
    if preamble.strip():
        output.extend(
            (part, start, end, None)
            for part, start, end in _offset_recursive_pieces(preamble, chunk_size)
        )

    for index, match in enumerate(matches):
        level = len(match.group(1))
        title = match.group(2).strip()
        while stack and stack[-1][0] >= level:
            stack.pop()
        stack.append((level, title))
        section_start = match.start()
        section_end = matches[index + 1].start() if index + 1 < len(matches) else len(document.text)
        section = document.text[section_start:section_end]
        header_path = " > ".join(item[1] for item in stack)
        for part, local_start, local_end in _offset_recursive_pieces(section, chunk_size):
            output.append(
                (part, section_start + local_start, min(section_start + local_end, section_end), header_path)
            )
    return output


def _offset_recursive_pieces(text: str, chunk_size: int) -> list[tuple[str, int, int]]:
    pieces = _recursive_pieces(text, chunk_size, ("\n\n", "\n", "。", "！", "？", "；", "，", " "))
    result: list[tuple[str, int, int]] = []
    cursor = 0
    for piece in pieces:
        start = text.find(piece, cursor)
        if start < 0:
            start = cursor
        end = start + len(piece)
        result.append((piece, start, end))
        cursor = end
    return result


def header_structure_chunks(
    document: CampusDocument,
    *,
    chunk_size: int = 700,
) -> list[TextChunk]:
    if chunk_size < 1:
        raise ValueError("chunk_size must be positive.")
    pieces = _section_chunks(document, chunk_size)
    return _to_chunks(
        document,
        pieces,
        strategy="header_structure",
        config=f"size={chunk_size}",
    )

