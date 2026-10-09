"""Build the initial campus chunk and local-embedding baseline on Windows."""

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


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def chunk_summary(chunks: list) -> dict:
    lengths = [len(chunk.text) for chunk in chunks]
    return {
        "chunk_count": len(chunks),
        "min_characters": min(lengths) if lengths else 0,
        "max_characters": max(lengths) if lengths else 0,
        "mean_characters": round(sum(lengths) / len(lengths), 2) if lengths else 0,
        "source_count": len({chunk.source_id for chunk in chunks}),
    }


def main() -> int:
    if sys.platform != "win32":
        raise SystemExit("Run the campus indexing experiment with the Windows project venv.")

    started = datetime.now(ZoneInfo("Asia/Shanghai"))
    run_id = started.strftime("campus-index-%Y%m%d-%H%M%S")
    run_dir = ROOT / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    manifest_path = ROOT / "docs" / "campus" / "source_manifest.json"
    manifest = {
        "run_id": run_id,
        "started_at": started.isoformat(timespec="seconds"),
        "platform": sys.platform,
        "source_manifest_sha256": sha256(manifest_path),
        "course_answer_result": False,
        "paid_api_request_performed": False,
        "document_count": None,
        "chunks": {},
        "embedding": {"model": "bge-m3:latest", "complete": False},
        "retrieval_queries": [],
        "errors": [],
    }
    (run_dir / "progress.jsonl").write_text("", encoding="utf-8")
    progress_path = run_dir / "progress.jsonl"

    def progress(event: dict) -> None:
        with progress_path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
        print(json.dumps(event, ensure_ascii=False), flush=True)

    try:
        documents = load_campus_documents(manifest_path)
        manifest["document_count"] = len(documents)
        fixed = [chunk for document in documents for chunk in fixed_length_chunks(document)]
        recursive = [
            chunk for document in documents for chunk in recursive_boundary_chunks(document)
        ]
        structured = [
            chunk for document in documents for chunk in header_structure_chunks(document)
        ]
        manifest["chunks"] = {
            "fixed_length_size500_overlap80": chunk_summary(fixed),
            "recursive_size500_overlap80": chunk_summary(recursive),
            "header_structure_size700": chunk_summary(structured),
        }
        if len(fixed) < 20:
            raise ValueError(f"Expected at least 20 fixed-length chunks; found {len(fixed)}.")

        (run_dir / "chunking_summary.json").write_text(
            json.dumps(manifest["chunks"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        with (run_dir / "chunks.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
            for chunk in fixed:
                handle.write(
                    json.dumps(
                        {
                            "chunk_id": chunk.chunk_id,
                            "source_id": chunk.source_id,
                            "text": chunk.text,
                            "metadata": chunk.metadata,
                        },
                        ensure_ascii=False,
                        sort_keys=True,
                    )
                    + "\n"
                )

        embedder = OllamaBGEEmbeddings(batch_size=8, timeout_seconds=90)
        vectors: list[list[float]] = []
        batch_count = (len(fixed) + embedder.batch_size - 1) // embedder.batch_size
        for batch_index, start in enumerate(range(0, len(fixed), embedder.batch_size), start=1):
            batch = fixed[start : start + embedder.batch_size]
            batch_started = time.monotonic()
            result = embedder.embed_documents([chunk.text for chunk in batch])
            vectors.extend(result.vectors)
            progress(
                {
                    "stage": "embedding",
                    "batch": batch_index,
                    "batches_total": batch_count,
                    "chunks_completed": len(vectors),
                    "chunks_total": len(fixed),
                    "dimension": result.dimension,
                    "duration_seconds": round(time.monotonic() - batch_started, 2),
                }
            )

        matrix = np.asarray(vectors, dtype=np.float32)
        if matrix.shape != (len(fixed), 1024):
            raise ValueError(f"Unexpected embedding matrix shape: {matrix.shape}.")
        np.savez_compressed(run_dir / "fixed_500_embeddings.npz", vectors=matrix)
        manifest["embedding"] = {
            "model": embedder.model,
            "base_url": embedder.base_url,
            "complete": True,
            "chunk_count": len(fixed),
            "dimension": int(matrix.shape[1]),
            "batch_size": embedder.batch_size,
            "batch_count": batch_count,
            "automatic_retries": 0,
            "vectors_saved": "fixed_500_embeddings.npz",
            "embedding_values_in_report": False,
        }

        queries = [
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
        retrieval_rows = []
        for query in queries:
            query_vector = embedder.embed_query(query["query"])
            hits = cosine_search(query_vector, fixed, matrix, top_k=5)
            ranks = [hit.rank for hit in hits if hit.chunk.source_id in query["expected_source_ids"]]
            row = {
                "query_id": query["query_id"],
                "expected_unknown": query.get("expected_unknown", False),
                "expected_source_ids": query["expected_source_ids"],
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
            retrieval_rows.append(row)
            progress({"stage": "retrieval", "query_id": query["query_id"], "top1": row["hits"][0]})

        manifest["retrieval_queries"] = retrieval_rows
        manifest["mean_reciprocal_rank_at_5"] = round(
            sum(row["reciprocal_rank"] for row in retrieval_rows) / len(retrieval_rows), 6
        )
        (run_dir / "retrieval_top5.json").write_text(
            json.dumps(retrieval_rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        manifest["completed"] = True
    except Exception as error:
        manifest["errors"].append({"type": type(error).__name__})
        manifest["completed"] = False
        manifest["error_message"] = str(error)[:500]
    finally:
        finished = datetime.now(ZoneInfo("Asia/Shanghai"))
        manifest["finished_at"] = finished.isoformat(timespec="seconds")
        manifest["duration_seconds"] = round((finished - started).total_seconds(), 3)
        (run_dir / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    print(
        json.dumps(
            {
                "run_id": run_id,
                "completed": manifest.get("completed", False),
                "document_count": manifest["document_count"],
                "chunk_count": manifest["embedding"].get("chunk_count"),
                "dimension": manifest["embedding"].get("dimension"),
                "errors": manifest["errors"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if manifest.get("completed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
