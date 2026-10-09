"""Inspect extracted text in downloaded university PDFs without changing them."""

from __future__ import annotations

import sys
from pathlib import Path

from pypdf import PdfReader


def main() -> int:
    if sys.platform != "win32":
        raise SystemExit("Run with the Windows project venv.")
    raw = Path(__file__).resolve().parents[1] / "docs" / "campus" / "raw"
    for path in sorted(raw.glob("*.pdf")):
        reader = PdfReader(str(path))
        pages = [page.extract_text() or "" for page in reader.pages]
        preview = " | ".join(" ".join(page.split())[:180] for page in pages[:2])
        print(f"{path.name}: pages={len(pages)}, chars={sum(map(len, pages))}")
        print(f"  preview={preview}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
