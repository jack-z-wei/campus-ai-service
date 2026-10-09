"""Fetch a curated set of official Chang'an University sources on Windows."""

from __future__ import annotations

import hashlib
import json
import re
import sys
import time
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

import requests
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "data" / "campus" / "source_catalog.json"
RAW = ROOT / "docs" / "campus" / "raw"
DOCS = ROOT / "docs" / "campus"
USER_AGENT = "CampusCourseProjectSourceCollector/1.0 (official public pages only)"


class VisibleText(HTMLParser):
    BLOCKS = {
        "address", "article", "blockquote", "br", "dd", "div", "dl", "dt", "h1", "h2",
        "h3", "h4", "h5", "h6", "li", "main", "ol", "p", "section", "table", "td",
        "th", "tr", "ul",
    }
    SKIP = {"script", "style", "noscript", "svg", "head", "nav", "header", "footer"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in self.SKIP:
            self._skip_depth += 1
        elif self._skip_depth == 0 and tag in self.BLOCKS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self.SKIP and self._skip_depth:
            self._skip_depth -= 1
        elif self._skip_depth == 0 and tag in self.BLOCKS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0:
            self.parts.append(data)

    def text(self) -> str:
        lines = [re.sub(r"\s+", " ", line).strip() for line in "".join(self.parts).splitlines()]
        return "\n".join(line for line in lines if line)


def response_sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def extract_html_text(content: bytes, encoding: str | None) -> str:
    header_match = re.search(r"charset=([\w.-]+)", encoding or "", flags=re.IGNORECASE)
    meta_match = re.search(
        rb"<meta[^>]+charset\s*=\s*['\"]?([\w.-]+)", content[:4096], flags=re.IGNORECASE
    )
    charset = header_match.group(1) if header_match else (
        meta_match.group(1).decode("ascii") if meta_match else "utf-8"
    )
    text = content.decode(charset, errors="replace")
    parser = VisibleText()
    parser.feed(text)
    return parser.text()


def fetch_one(session: requests.Session, item: dict, index: int, count: int) -> dict:
    source_id = item["id"]
    host = (urlparse(item["url"]).hostname or "").lower()
    if not (host.endswith(".chd.edu.cn") or host == "chd.edu.cn"):
        raise ValueError(f"Source host is outside chd.edu.cn: {host}")

    print(f"[{index}/{count}] Fetching {source_id} ...", flush=True)
    response = session.get(item["url"], timeout=(10, 30), allow_redirects=True)
    response.raise_for_status()
    payload = response.content
    if not payload:
        raise ValueError("Empty response")

    raw_path = RAW / f"{source_id}.{ 'pdf' if item['kind'] == 'pdf' else 'html' }"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_bytes(payload)

    pages = None
    if item["kind"] == "pdf":
        if not payload.startswith(b"%PDF"):
            raise ValueError(f"Expected PDF, got {response.headers.get('Content-Type')}")
        reader = PdfReader(str(raw_path))
        page_text = [page.extract_text() or "" for page in reader.pages]
        body = "\n\n".join(f"## PDF 第 {page_no} 页\n\n{text}" for page_no, text in enumerate(page_text, 1))
        pages = len(reader.pages)
    elif item["kind"] == "library_home_snapshot":
        root_html = payload.decode(response.encoding or "utf-8", errors="replace")
        preview_match = re.search(r"var previewUrl = '([^']+)'", root_html)
        rendered_sha = None
        rendered_bytes = 0
        if preview_match:
            preview_url = requests.compat.urljoin(response.url, preview_match.group(1))
            rendered_response = session.get(preview_url, timeout=(10, 30), allow_redirects=True)
            rendered_response.raise_for_status()
            rendered_payload = rendered_response.content
            rendered_path = RAW / f"{source_id}_rendered.html"
            rendered_path.write_bytes(rendered_payload)
            rendered_sha = response_sha(rendered_payload)
            rendered_bytes = len(rendered_payload)
        body = (
            "本地文件是官网首页动态页面的人工核对摘要；页面原始 HTML 与服务端渲染快照保存在 raw/。\n\n"
            "官网显示的联系地址为西安市南二环路中段，图书馆电话为 +86-029-82334372，"
            "邮箱为 tsgbgs@chd.edu.cn。首页导航列有开放时间、借阅规则、校外访问、"
            "读者荐购、研讨间预约、文献传递和讲座培训等入口。\n\n"
            "抓取时首页公告列表包含《关于2026年图书馆中秋节、国庆节开放的通知》（2026-09-24）、"
            "《关于2026年图书馆暑期工作安排的通知》（2026-07-10）、"
            "《关于2026年图书馆清明节开放的通知》（2026-04-03）和"
            "《关于2026年图书馆寒假工作安排的通知》（2026-01-19）。\n\n"
            "此首页快照只证明服务入口、联系信息和公告标题/日期；不含公告正文，不能据此回答当前开放时段。"
        )
        item["rendered_sha256"] = rendered_sha
        item["rendered_bytes"] = rendered_bytes
        item["rendered_file"] = f"docs/campus/raw/{source_id}_rendered.html" if rendered_bytes else None
    else:
        body = extract_html_text(payload, response.headers.get("Content-Type"))
        pages = None

    target_path = DOCS / f"{source_id}.md"
    header = [
        f"# {item['title']}",
        "",
        f"- 来源：{item['url']}",
        f"- 官方发布/页面日期：{item['published_on']}",
        f"- HTTP Last-Modified：{response.headers.get('Last-Modified', '未提供')}",
        f"- 适用范围：{item['scope']}",
        f"- 主题：{item['category']}",
        f"- 检索策略：{item['index_policy']}",
            f"- 抓取时间（UTC）：{datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        f"- 原始文件：`raw/{raw_path.name}`（SHA-256 `{response_sha(payload)}`）",
        "",
        "## 原文文本快照",
        "",
    ]
    if not body.strip():
        raise ValueError("No extractable text; kept raw file for manual review")
    target_path.write_text("\n".join(header) + body.strip() + "\n", encoding="utf-8")

    return {
        **item,
        "fetch_status": "ok",
        "final_url": response.url,
        "http_status": response.status_code,
        "content_type": response.headers.get("Content-Type"),
        "last_modified": response.headers.get("Last-Modified"),
        "content_length_bytes": len(payload),
        "sha256": response_sha(payload),
        "raw_file": raw_path.relative_to(ROOT).as_posix(),
        "text_file": target_path.relative_to(ROOT).as_posix(),
        "pdf_pages": pages,
        "extracted_characters": len(body),
    }


def main() -> int:
    if sys.platform != "win32":
        raise SystemExit("Run this acquisition script with the Windows project venv.")
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    sources = catalog["sources"]
    DOCS.mkdir(parents=True, exist_ok=True)
    RAW.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept": "text/html,application/pdf,*/*"})
    results: list[dict] = []
    errors: list[dict] = []
    for index, item in enumerate(sources, 1):
        try:
            results.append(fetch_one(session, item, index, len(sources)))
        except Exception as exc:  # record per-source failures and keep the batch moving
            print(f"[{index}/{len(sources)}] FAILED {item['id']}: {type(exc).__name__}: {exc}", flush=True)
            errors.append({"id": item["id"], "url": item["url"], "error_type": type(exc).__name__, "error": str(exc)})
        if index < len(sources):
            time.sleep(0.25)

    manifest = {
        "captured_on": datetime.now().astimezone().isoformat(timespec="seconds"),
        "source_count": len(results),
        "category_count": len({item["category"] for item in results}),
        "sources": results,
        "errors": errors,
    }
    (DOCS / "source_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Finished: {len(results)}/{len(sources)} source snapshots, {len(errors)} errors.", flush=True)
    return 0 if results else 1


if __name__ == "__main__":
    raise SystemExit(main())
