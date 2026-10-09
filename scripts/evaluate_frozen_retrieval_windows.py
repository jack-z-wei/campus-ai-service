"""Evaluate all ten frozen knowledge questions on Windows with recorded vectors."""

from __future__ import annotations

import hashlib
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def unique_source_metrics(hits: list, relevant: list[str]) -> dict:
    ordered_source_ids = list(dict.fromkeys(hit.chunk.source_id for hit in hits))
    expected = set(relevant)
    first_rank = next(
        (
            rank
            for rank, source_id in enumerate(ordered_source_ids, start=1)
            if source_id in expected
        ),
        None,
    )
    return {
        f"recall_at_{k}": round(len(set(ordered_source_ids[:k]) & expected) / len(expected), 6)
        for k in (1, 3, 5)
    } | {"mrr_at_5": round(1 / first_rank, 6) if first_rank and first_rank <= 5 else 0.0}


def hit_payload(hits: list) -> list[dict]:
    return [
        {
            "rank": hit.rank,
            "source_id": hit.chunk.source_id,
            "chunk_id": hit.chunk.chunk_id,
            "score": round(hit.score, 8),
            "index_policy": hit.chunk.metadata.get("index_policy"),
        }
        for hit in hits
    ]


def mean_metrics(rows: list[dict]) -> dict:
    if not rows:
        return {}
    keys = ("recall_at_1", "recall_at_3", "recall_at_5", "mrr_at_5")
    return {key: round(sum(row[key] for row in rows) / len(rows), 6) for key in keys}


def main() -> int:
    if sys.platform != "win32":
        raise SystemExit("Run this retrieval evaluation with the Windows project .venv.")

    from campus.chunking import TextChunk
    from campus.embeddings import OllamaBGEEmbeddings
    from campus.retrieval import cosine_search
    from campus.retrieval_chroma import ChromaVectorIndex

    manifest_path = PROJECT_ROOT / "docs" / "campus" / "source_manifest.json"
    index_config_path = PROJECT_ROOT / "data" / "campus" / "index_config.json"
    config = json.loads(index_config_path.read_text(encoding="utf-8"))
    source_sha = sha256(manifest_path)
    if source_sha != config["source_manifest_sha256"]:
        raise SystemExit("The recorded index is stale: source manifest hash has changed.")
    chunk_run = PROJECT_ROOT / "runs" / config["chunk_run_id"]
    fixed_chunks: list[TextChunk] = []
    with (chunk_run / "chunks.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            item = json.loads(line)
            fixed_chunks.append(
                TextChunk(
                    chunk_id=item["chunk_id"],
                    source_id=item["source_id"],
                    text=item["text"],
                    metadata=item["metadata"],
                )
            )
    fixed_vectors = np.load(chunk_run / "fixed_500_embeddings.npz")["vectors"]
    if fixed_vectors.shape[0] != len(fixed_chunks):
        raise SystemExit("Recorded fixed-length vectors do not match the recorded chunks.")

    cases_path = PROJECT_ROOT / "evaluation" / "frozen_cases.json"
    dataset = json.loads(cases_path.read_text(encoding="utf-8"))
    queries = [case for case in dataset["cases"] if case["category"] == "knowledge"]
    if len(queries) != 10:
        raise SystemExit(f"Expected ten frozen knowledge cases, found {len(queries)}.")

    started = datetime.now(ZoneInfo("Asia/Shanghai"))
    run_id = started.strftime("retrieval-frozen10-%Y%m%d-%H%M%S")
    run_dir = PROJECT_ROOT / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    progress_path = run_dir / "progress.jsonl"
    results_path = run_dir / "per_case.jsonl"
    progress_path.write_text("", encoding="utf-8")
    results_path.write_text("", encoding="utf-8")
    chroma_run = PROJECT_ROOT / "runs" / config["chroma_run_id"]
    chroma = ChromaVectorIndex(chroma_run / "chroma_db", config["chroma_collection"])
    embedder = OllamaBGEEmbeddings(
        model=config["embedding"]["model"], batch_size=1, timeout_seconds=90
    )
    archive_policy = "archive_not_for_current_answers"
    variants: dict[str, list[dict]] = {
        "raw_numpy": [],
        "policy_filtered_numpy": [],
        "policy_filtered_chroma": [],
    }
    errors = []
    query_started = time.monotonic()

    for case in queries:
        case_id = case["case_id"]
        query = case["turns"][0]["content"]
        expected = case["gold"]["source_ids"]
        try:
            query_vector = embedder.embed_query(query)
            comparisons = {
                "raw_numpy": cosine_search(query_vector, fixed_chunks, fixed_vectors, top_k=5),
                "policy_filtered_numpy": cosine_search(
                    query_vector,
                    fixed_chunks,
                    fixed_vectors,
                    top_k=5,
                    exclude_index_policies={archive_policy},
                ),
                "policy_filtered_chroma": chroma.search(
                    query_vector,
                    top_k=5,
                    exclude_index_policies={archive_policy},
                ),
            }
            row = {
                "case_id": case_id,
                "question": query,
                "expected_source_ids": expected,
                "variants": {
                    name: {
                        "retrieved_chunks": hit_payload(hits),
                        "retrieved_source_ids": list(
                            dict.fromkeys(hit.chunk.source_id for hit in hits)
                        ),
                        "metrics": unique_source_metrics(hits, expected),
                    }
                    for name, hits in comparisons.items()
                },
            }
            for name, value in row["variants"].items():
                variants[name].append(value["metrics"])
            with results_path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            progress = {
                "case_id": case_id,
                "raw_numpy_top1": row["variants"]["raw_numpy"]["retrieved_chunks"][:1],
                "filtered_numpy_top1": row["variants"]["policy_filtered_numpy"]["retrieved_chunks"][
                    :1
                ],
                "filtered_chroma_top1": row["variants"]["policy_filtered_chroma"][
                    "retrieved_chunks"
                ][:1],
            }
            with progress_path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(progress, ensure_ascii=False) + "\n")
            print(f"completed {case_id}", flush=True)
        except Exception as error:
            errors.append({"case_id": case_id, "error_type": type(error).__name__})
            with progress_path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(errors[-1], ensure_ascii=False) + "\n")
            print(f"failed {case_id}: {type(error).__name__}", flush=True)

    manifest = {
        "run_id": run_id,
        "started_at": started.isoformat(timespec="seconds"),
        "finished_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds"),
        "platform": sys.platform,
        "course_answer_evaluation": False,
        "paid_api_request_performed": False,
        "source_manifest_sha256": source_sha,
        "frozen_cases_sha256": sha256(cases_path),
        "index_id": config["index_id"],
        "query_count": len(queries),
        "completed_query_count": len(queries) - len(errors),
        "elapsed_seconds": round(time.monotonic() - query_started, 3),
        "source_rank_definition": "Deduplicate ranked chunks by source_id; relevant source IDs come from the frozen gold set.",
        "variants": {name: mean_metrics(rows) for name, rows in variants.items()},
        "failed_queries": errors,
        "answer_quality_or_abstention_measured": False,
        "per_case_file": "per_case.jsonl",
        "progress_file": "progress.jsonl",
    }
    (run_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2), flush=True)
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
