"""Load only allowlisted campus source snapshots from the source manifest."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = PROJECT_ROOT / "docs" / "campus" / "source_manifest.json"


@dataclass(frozen=True, slots=True)
class CampusDocument:
    source_id: str
    text: str
    metadata: dict[str, Any]


def _inside(root: Path, path: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def load_campus_documents(
    manifest_path: Path = DEFAULT_MANIFEST,
    *,
    verify_raw_hash: bool = True,
) -> list[CampusDocument]:
    """Read UTF-8 text only for manifest entries; reject missing or escaping paths."""
    manifest_path = manifest_path.resolve()
    root = PROJECT_ROOT.resolve()
    if not _inside(root, manifest_path):
        raise ValueError("Source manifest must be located inside the project root.")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    sources = manifest.get("sources")
    if not isinstance(sources, list) or manifest.get("source_count") != len(sources):
        raise ValueError("Source manifest is missing a consistent source list.")

    documents: list[CampusDocument] = []
    seen_ids: set[str] = set()
    for source in sources:
        source_id = source.get("id")
        if not isinstance(source_id, str) or not source_id or source_id in seen_ids:
            raise ValueError(f"Invalid or duplicate source ID: {source_id!r}")
        seen_ids.add(source_id)

        if source.get("fetch_status") != "ok":
            raise ValueError(f"Source {source_id} was not captured successfully.")
        text_rel = source.get("text_file")
        raw_rel = source.get("raw_file")
        if not isinstance(text_rel, str) or Path(text_rel).suffix.lower() != ".md":
            raise ValueError(f"Source {source_id} does not point to an approved Markdown snapshot.")
        text_path = (root / text_rel).resolve()
        if not _inside(root, text_path) or not text_path.is_file():
            raise ValueError(f"Source snapshot is missing or escapes project root: {text_rel}")

        if verify_raw_hash:
            if not isinstance(raw_rel, str):
                raise ValueError(f"Source {source_id} has no raw-file reference.")
            raw_path = (root / raw_rel).resolve()
            if not _inside(root, raw_path) or not raw_path.is_file():
                raise ValueError(f"Source raw file is missing or escapes project root: {raw_rel}")
            digest = hashlib.sha256(raw_path.read_bytes()).hexdigest()
            if digest != source.get("sha256"):
                raise ValueError(f"Source raw-file SHA-256 mismatch: {source_id}")

        text = text_path.read_text(encoding="utf-8").strip()
        if not text:
            raise ValueError(f"Source snapshot is empty: {source_id}")
        if "\ufffd" in text:
            raise ValueError(f"Source snapshot contains replacement characters: {source_id}")

        metadata = {
            "source_id": source_id,
            "title": source.get("title"),
            "category": source.get("category"),
            "url": source.get("url"),
            "published_on": source.get("published_on"),
            "scope": source.get("scope"),
            "index_policy": source.get("index_policy"),
            "source_sha256": source.get("sha256"),
            "source_file": text_rel,
            "last_modified": source.get("last_modified"),
        }
        documents.append(CampusDocument(source_id=source_id, text=text, metadata=metadata))

    return documents

