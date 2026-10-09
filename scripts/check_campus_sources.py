"""Check the integrity and scope metadata of captured official source files."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs" / "campus" / "source_manifest.json"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    if sys.platform != "win32":
        raise SystemExit("Run this source integrity check with the Windows project venv.")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    issues: list[str] = []
    sources = manifest.get("sources", [])
    if manifest.get("source_count") != len(sources):
        issues.append("source_count does not match source list")
    if manifest.get("errors"):
        issues.append(f"acquisition errors recorded: {len(manifest['errors'])}")

    categories = {source.get("category") for source in sources}
    required_categories = {"教务", "奖助", "宿舍", "图书馆"}
    missing = sorted(required_categories - categories)
    if missing:
        issues.append(f"missing source categories: {', '.join(missing)}")

    for source in sources:
        raw_rel = source.get("raw_file")
        text_rel = source.get("text_file")
        raw_path = ROOT / raw_rel if raw_rel else None
        text_path = ROOT / text_rel if text_rel else None
        if not raw_path or not raw_path.is_file():
            issues.append(f"missing raw file: {raw_rel}")
            continue
        if digest(raw_path) != source.get("sha256"):
            issues.append(f"SHA-256 mismatch: {raw_rel}")
        if not text_path or not text_path.is_file():
            issues.append(f"missing text snapshot: {text_rel}")
            continue
        text = text_path.read_text(encoding="utf-8")
        if "\ufffd" in text:
            issues.append(f"replacement characters in text snapshot: {text_rel}")
        if source.get("extracted_characters", 0) < 100:
            issues.append(f"very short text snapshot: {text_rel}")
        rendered_rel = source.get("rendered_file")
        if rendered_rel:
            rendered_path = ROOT / rendered_rel
            if not rendered_path.is_file() or digest(rendered_path) != source.get("rendered_sha256"):
                issues.append(f"missing or mismatched rendered snapshot: {rendered_rel}")

    print(f"sources={len(sources)} categories={len(categories)} errors={len(issues)}")
    for source in sources:
        print(f"{source['id']}: {source['category']} / {source['index_policy']} / {source['extracted_characters']} chars")
    for issue in issues:
        print(f"ERROR: {issue}")
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
