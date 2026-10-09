"""Compare raw and source-policy-filtered NumPy/Chroma retrieval on Windows."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from campus.chunking import TextChunk
from campus.embeddings import OllamaBGEEmbeddings
from campus.retrieval import cosine_search
from campus.retrieval_chroma import ChromaVectorIndex


ARCHIVE_POLICY = "archive_not_for_current_answers"
QUERIES = [
    {
        "query_id": "K01",
        "query": "长安大学本科生每学期修读多少学分比较合适？",
        "expected_source_ids": ["academic_course_selection_2022"],
    },
    {
        "query_id": "K10",
        "query": "长安大学图书馆官网公开的联系电话和邮箱是什么？",
        "expected_source_ids": ["library_home_2026"],
    },
    {
        "query_id": "U01",
        "query": "长安大学图书馆今天所有馆区具体几点开门、几点闭馆？",
        "expected_source_ids": ["library_home_2026"],
        "expected_unknown": True,
    },
]


def rank_row(hits, query: dict) -> dict:
    expected = set(query["expected_source_ids"])
    ranks = [hit.rank for hit in hits if hit.chunk.source_id in expected]
    return {
        "query_id": query["query_id"],
        "expected_unknown": query.get("expected_unknown", False),
        "expected_source_ids": sorted(expected),
        "reciprocal_rank": round(1 / min(ranks), 6) if ranks else 0.0,
        "hits": [
            {
                "rank": hit.rank,
                "score": round(hit.score, 8),
                "source_id": hit.chunk.source_id,
                "chunk_id": hit.chunk.chunk_id,
                "index_policy": hit.chunk.metadata.get("index_policy"),
            }
            for hit in hits
        ],
    }


def mrr(rows: list[dict]) -> float:
    return round(sum(row["reciprocal_rank"] for row in rows) / len(rows), 6)


def main() -> int:
    if sys.platform != "win32":
        raise SystemExit("Run the retrieval policy experiment with the Windows project venv.")
    parser = argparse.ArgumentParser()
    parser.add_argument("baseline_run_id", help="Existing campus-index run directory name")
    args = parser.parse_args()

    baseline_dir = ROOT / "runs" / args.baseline_run_id
    if not baseline_dir.is_dir():
        raise SystemExit("Baseline run directory not found.")
    source_manifest = ROOT / "docs" / "campus" / "source_manifest.json"
    recorded = json.loads((baseline_dir / "manifest.json").read_text(encoding="utf-8"))
    source_sha = hashlib.sha256(source_manifest.read_bytes()).hexdigest()
    if source_sha != recorded.get("source_manifest_sha256"):
        raise SystemExit("Baseline source manifest hash differs from the current source manifest.")

    chunks: list[TextChunk] = []
    with (baseline_dir / "chunks.jsonl").open(encoding="utf-8") as handle:
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
    vectors = np.load(baseline_dir / "fixed_500_embeddings.npz")["vectors"]
    if vectors.shape[0] != len(chunks):
        raise SystemExit("Baseline vector count does not match the chunk file.")

    started = datetime.now(ZoneInfo("Asia/Shanghai"))
    run_id = started.strftime("retrieval-policy-%Y%m%d-%H%M%S")
    run_dir = ROOT / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    manifest = {
        "run_id": run_id,
        "started_at": started.isoformat(timespec="seconds"),
        "platform": sys.platform,
        "baseline_run_id": args.baseline_run_id,
        "source_manifest_sha256": source_sha,
        "paid_api_request_performed": False,
        "course_answer_result": False,
        "excluded_index_policies": [ARCHIVE_POLICY],
        "answer_abstention_evaluated": False,
        "errors": [],
    }
    progress_path = run_dir / "progress.jsonl"
    progress_path.write_text("", encoding="utf-8")
    try:
        embedder = OllamaBGEEmbeddings(batch_size=8, timeout_seconds=90)
        query_vectors = embedder.embed_documents([item["query"] for item in QUERIES]).vectors
        index = ChromaVectorIndex(run_dir / "chroma_db", "campus-policy-filter-v1")
        index.add_chunks(chunks, vectors)
        comparisons = []
        for query, query_vector in zip(QUERIES, query_vectors, strict=True):
            raw = rank_row(cosine_search(query_vector, chunks, vectors, top_k=5), query)
            filtered = rank_row(
                cosine_search(
                    query_vector,
                    chunks,
                    vectors,
                    top_k=5,
                    exclude_index_policies={ARCHIVE_POLICY},
                ),
                query,
            )
            chroma = rank_row(
                index.search(
                    query_vector,
                    top_k=5,
                    exclude_index_policies={ARCHIVE_POLICY},
                ),
                query,
            )
            comparisons.append(
                {"query_id": query["query_id"], "raw_numpy": raw, "policy_filtered_numpy": filtered, "policy_filtered_chroma": chroma}
            )
            progress = {
                "query_id": query["query_id"],
                "raw_top1": raw["hits"][0] if raw["hits"] else None,
                "filtered_numpy_top1": filtered["hits"][0] if filtered["hits"] else None,
                "filtered_chroma_top1": chroma["hits"][0] if chroma["hits"] else None,
            }
            with progress_path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(progress, ensure_ascii=False) + "\n")
            print(json.dumps(progress, ensure_ascii=False), flush=True)

        summary = {
            "raw_numpy_mrr_at_5": mrr([item["raw_numpy"] for item in comparisons]),
            "policy_filtered_numpy_mrr_at_5": mrr(
                [item["policy_filtered_numpy"] for item in comparisons]
            ),
            "policy_filtered_chroma_mrr_at_5": mrr(
                [item["policy_filtered_chroma"] for item in comparisons]
            ),
            "query_count": len(comparisons),
            "known_answer_queries": 2,
            "unknown_answer_query": 1,
            "unknown_answer_quality_measured": False,
        }
        manifest.update({"completed": True, "summary": summary, "comparisons": comparisons})
    except Exception as error:
        manifest["completed"] = False
        manifest["errors"].append({"type": type(error).__name__, "message": str(error)[:500]})
    finally:
        manifest["finished_at"] = datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds")
        (run_dir / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    print(json.dumps({"run_id": run_id, "completed": manifest.get("completed"), "summary": manifest.get("summary"), "errors": manifest["errors"]}, ensure_ascii=False))
    return 0 if manifest.get("completed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
