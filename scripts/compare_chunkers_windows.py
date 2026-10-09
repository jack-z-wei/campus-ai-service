"""Compare three campus chunking variants on the same local retrieval queries."""

from __future__ import annotations

import hashlib
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from campus.chunking import fixed_length_chunks, header_structure_chunks, recursive_boundary_chunks
from campus.embeddings import OllamaBGEEmbeddings
from campus.ingestion import load_campus_documents
from campus.retrieval import cosine_search


EXCLUDED_POLICIES = {"archive_not_for_current_answers"}
QUERIES = [
    ("K01", "长安大学本科生每学期修读多少学分比较合适？", "academic_course_selection_2022"),
    ("K10", "长安大学图书馆官网公开的联系电话和邮箱是什么？", "library_home_2026"),
    ("U01", "长安大学图书馆今天所有馆区具体几点开门、几点闭馆？", "library_home_2026"),
]


def retrieve(chunks, vectors, query_vector, expected_source_id: str, strategy: str) -> dict:
    result = {}
    for label, excluded in (("raw", None), ("policy_filtered", EXCLUDED_POLICIES)):
        hits = cosine_search(
            query_vector,
            chunks,
            vectors,
            top_k=5,
            exclude_index_policies=excluded,
        )
        ranks = [hit.rank for hit in hits if hit.chunk.source_id == expected_source_id]
        result[label] = {
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
    return {"strategy": strategy, **result}


def mean_reciprocal_rank(rows: list[dict], mode: str) -> float:
    return round(sum(row[mode]["reciprocal_rank"] for row in rows) / len(rows), 6)


def main() -> int:
    if sys.platform != "win32":
        raise SystemExit("Run the chunking experiment with the Windows project venv.")
    started = datetime.now(ZoneInfo("Asia/Shanghai"))
    run_id = started.strftime("chunking-compare-%Y%m%d-%H%M%S")
    run_dir = ROOT / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    source_manifest = ROOT / "docs" / "campus" / "source_manifest.json"
    manifest = {
        "run_id": run_id,
        "started_at": started.isoformat(timespec="seconds"),
        "platform": sys.platform,
        "source_manifest_sha256": hashlib.sha256(source_manifest.read_bytes()).hexdigest(),
        "paid_api_request_performed": False,
        "course_answer_result": False,
        "embedding_model": "bge-m3:latest",
        "embedding_dimension": 1024,
        "batch_size": 8,
        "comparisons": [],
        "errors": [],
    }
    progress_path = run_dir / "progress.jsonl"
    progress_path.write_text("", encoding="utf-8")

    def log_progress(event: dict) -> None:
        with progress_path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")
        print(json.dumps(event, ensure_ascii=False), flush=True)

    try:
        documents = load_campus_documents(source_manifest)
        query_embedder = OllamaBGEEmbeddings(batch_size=8, timeout_seconds=90)
        query_vectors = query_embedder.embed_documents([item[1] for item in QUERIES]).vectors
        embedders = OllamaBGEEmbeddings(batch_size=8, timeout_seconds=90)
        strategies = {
            "fixed_size500_overlap80": lambda doc: fixed_length_chunks(doc, chunk_size=500, overlap=80),
            "recursive_size500_overlap80": lambda doc: recursive_boundary_chunks(doc, chunk_size=500, overlap=80),
            "header_size700": lambda doc: header_structure_chunks(doc, chunk_size=700),
        }

        for strategy, chunker in strategies.items():
            chunks = [chunk for document in documents for chunk in chunker(document)]
            vectors: list[list[float]] = []
            total_batches = (len(chunks) + embedders.batch_size - 1) // embedders.batch_size
            for batch_number, start in enumerate(range(0, len(chunks), embedders.batch_size), start=1):
                batch_started = time.monotonic()
                result = embedders.embed_documents(
                    [chunk.text for chunk in chunks[start : start + embedders.batch_size]]
                )
                vectors.extend(result.vectors)
                log_progress(
                    {
                        "strategy": strategy,
                        "batch": batch_number,
                        "batches_total": total_batches,
                        "chunks_completed": len(vectors),
                        "chunks_total": len(chunks),
                        "dimension": result.dimension,
                        "duration_seconds": round(time.monotonic() - batch_started, 2),
                    }
                )
            matrix = np.asarray(vectors, dtype=np.float32)
            if matrix.shape != (len(chunks), 1024):
                raise ValueError(f"{strategy}: unexpected vector shape {matrix.shape}.")

            query_results = []
            for (query_id, _query_text, expected_source_id), query_vector in zip(
                QUERIES, query_vectors, strict=True
            ):
                row = retrieve(chunks, matrix, query_vector, expected_source_id, strategy)
                query_results.append({"query_id": query_id, **row})
            lengths = [len(chunk.text) for chunk in chunks]
            manifest["comparisons"].append(
                {
                    "strategy": strategy,
                    "chunk_count": len(chunks),
                    "min_characters": min(lengths),
                    "max_characters": max(lengths),
                    "mean_characters": round(sum(lengths) / len(lengths), 2),
                    "raw_numpy_mrr_at_5": mean_reciprocal_rank(query_results, "raw"),
                    "policy_filtered_numpy_mrr_at_5": mean_reciprocal_rank(query_results, "policy_filtered"),
                    "query_results": query_results,
                }
            )
            log_progress(
                {
                    "strategy_complete": strategy,
                    "chunk_count": len(chunks),
                    "raw_numpy_mrr_at_5": manifest["comparisons"][-1]["raw_numpy_mrr_at_5"],
                    "policy_filtered_numpy_mrr_at_5": manifest["comparisons"][-1]["policy_filtered_numpy_mrr_at_5"],
                }
            )

        manifest["completed"] = True
    except Exception as error:
        manifest["completed"] = False
        manifest["errors"].append({"type": type(error).__name__, "message": str(error)[:500]})
    finally:
        manifest["finished_at"] = datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds")
        (run_dir / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    print(
        json.dumps(
            {
                "run_id": run_id,
                "completed": manifest.get("completed"),
                "strategies": [
                    {
                        "strategy": item["strategy"],
                        "chunk_count": item["chunk_count"],
                        "raw_numpy_mrr_at_5": item["raw_numpy_mrr_at_5"],
                        "policy_filtered_numpy_mrr_at_5": item["policy_filtered_numpy_mrr_at_5"],
                    }
                    for item in manifest["comparisons"]
                ],
                "errors": manifest["errors"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if manifest.get("completed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
