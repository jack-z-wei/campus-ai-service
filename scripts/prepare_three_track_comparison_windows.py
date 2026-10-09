"""Build a trace-backed three-track comparison sheet on the Windows project environment."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "reports" / "three_track_comparison.csv"
RUNS = {
    "principles": ROOT / "runs" / "baseline-optimized-principles-v1-20261006",
    "engineering": ROOT / "runs" / "baseline-optimized-engineering-v1-20261006",
}
CASES = ("K01", "S02")
TRACKS = ("python_principles", "langgraph_engineering", "coze")
FIELDS = (
    "case_id",
    "category",
    "track",
    "question",
    "simulation_user_id",
    "model",
    "prompt_sha256",
    "source_manifest_sha256",
    "frozen_cases_sha256",
    "actual_answer",
    "retrieved_source_ids",
    "actual_tool_names",
    "actual_tool_arguments",
    "actual_tool_outcomes",
    "elapsed_ms",
    "latency_definition",
    "execution_status",
    "error",
    "run_id",
    "evidence_path",
    "notes",
)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _tool_arguments(call: dict[str, Any]) -> dict[str, Any]:
    raw = call.get("arguments", call.get("args", {}))
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            raw = {"unparsed": raw}
    return raw if isinstance(raw, dict) else {"value": raw}


def _principles_result(case_id: str, case: dict[str, Any]) -> dict[str, Any]:
    parent = RUNS["principles"]
    index = next(
        item
        for item in map(json.loads, (parent / "per_case.jsonl").read_text(encoding="utf-8").splitlines())
        if item["case_id"] == case_id
    )
    run_id = index["run_id"]
    run_dir = ROOT / "runs" / run_id
    manifest = read_json(run_dir / "manifest.json")
    trace = read_json(run_dir / manifest.get("trace_file", "trace.json"))
    calls = trace.get("tool_calls", [])
    evidence = trace.get("retrieval", {}).get("evidence", [])
    source_ids = list(
        dict.fromkeys(item["source_id"] for item in evidence if item.get("rank") is not None)
    )
    elapsed_ms = trace.get("retrieval", {}).get("latency_ms", 0) + sum(
        item.get("latency_ms", 0) for item in trace.get("model_requests", [])
    )
    outcomes = []
    for item in trace.get("tool_results", []):
        result = item.get("result", {})
        outcomes.append(result.get("outcome", result))
    return {
        "model": manifest.get("chat_model", ""),
        "prompt_sha256": manifest.get("prompt_sha256", ""),
        "source_manifest_sha256": manifest.get("source_manifest_sha256", ""),
        "frozen_cases_sha256": manifest.get("frozen_cases_sha256", ""),
        "actual_answer": trace.get("answer", ""),
        "retrieved_source_ids": source_ids,
        "actual_tool_names": [item.get("name", "") for item in calls],
        "actual_tool_arguments": [_tool_arguments(item) for item in calls],
        "actual_tool_outcomes": outcomes,
        "elapsed_ms": round(elapsed_ms, 1),
        "latency_definition": "retrieval latency + provider round-trip latency; local tool/rendering overhead excluded",
        "execution_status": manifest.get("status", "unknown"),
        "error": manifest.get("error_type") or "",
        "run_id": run_id,
        "evidence_path": str((run_dir / "trace.json").relative_to(ROOT)),
        "notes": "Windows project .venv; optimized frozen-set run; timing scope differs from Engineering.",
    }


def _engineering_result(case_id: str) -> dict[str, Any]:
    parent = RUNS["engineering"]
    index = next(
        item
        for item in map(json.loads, (parent / "per_case.jsonl").read_text(encoding="utf-8").splitlines())
        if item["case_id"] == case_id
    )
    run_id = index["run_id"]
    run_dir = ROOT / "runs" / run_id
    manifest = read_json(run_dir / "manifest.json")
    trace = read_json(run_dir / "traces" / "turn_01.json")
    calls = trace.get("tool_calls", [])
    sources: list[str] = []
    for item in trace.get("tool_results", []):
        result = item.get("result", {})
        if isinstance(result, dict):
            for found in result.get("results", []):
                source_id = found.get("source_id")
                if source_id and source_id not in sources:
                    sources.append(source_id)
    outcomes = []
    for item in trace.get("tool_results", []):
        result = item.get("result", {})
        outcomes.append(result.get("outcome", result))
    return {
        "model": manifest.get("model", ""),
        "prompt_sha256": manifest.get("prompt_sha256", ""),
        "source_manifest_sha256": manifest.get("source_manifest_sha256", ""),
        "frozen_cases_sha256": manifest.get("frozen_cases_sha256", ""),
        "actual_answer": trace.get("answer", ""),
        "retrieved_source_ids": sources,
        "actual_tool_names": [item.get("name", "") for item in calls],
        "actual_tool_arguments": [_tool_arguments(item) for item in calls],
        "actual_tool_outcomes": outcomes,
        "elapsed_ms": round(trace.get("elapsed_seconds", 0) * 1000, 1),
        "latency_definition": "LangGraph ainvoke wall-clock duration including model/tool execution",
        "execution_status": trace.get("status", manifest.get("status", "unknown")),
        "error": trace.get("error") or "",
        "run_id": run_id,
        "evidence_path": str((run_dir / "traces" / "turn_01.json").relative_to(ROOT)),
        "notes": "Windows project .venv; optimized frozen-set run; timing scope differs from Principles.",
    }


def _pending_coze() -> dict[str, Any]:
    return {
        "model": "",
        "prompt_sha256": "",
        "source_manifest_sha256": "",
        "frozen_cases_sha256": "",
        "actual_answer": "",
        "retrieved_source_ids": [],
        "actual_tool_names": [],
        "actual_tool_arguments": [],
        "actual_tool_outcomes": [],
        "elapsed_ms": "",
        "latency_definition": "",
        "execution_status": "待平台实测",
        "error": "",
        "run_id": "",
        "evidence_path": "",
        "notes": "H-02：在真实 Coze 工作空间运行同一原题后填写；不得复制本地输出。",
    }


def build_rows() -> list[dict[str, Any]]:
    dataset = read_json(ROOT / "evaluation" / "frozen_cases.json")
    by_id = {case["case_id"]: case for case in dataset["cases"]}
    rows = []
    for case_id in CASES:
        case = by_id[case_id]
        question = case["turns"][0]["content"]
        identity = case.get("context", {}).get("authenticated_user_id", "")
        common = {
            "case_id": case_id,
            "category": case["category"],
            "question": question,
            "simulation_user_id": identity or "",
        }
        for track in TRACKS:
            if track == "python_principles":
                result = _principles_result(case_id, case)
            elif track == "langgraph_engineering":
                result = _engineering_result(case_id)
            else:
                result = _pending_coze()
            rows.append({**common, "track": track, **result})
    return rows


def encode(row: dict[str, Any]) -> dict[str, Any]:
    return {
        key: json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else value
        for key, value in row.items()
    }


def check_rows(rows: list[dict[str, Any]]) -> None:
    expected = {(case, track) for case in CASES for track in TRACKS}
    observed = {(row["case_id"], row["track"]) for row in rows}
    if len(rows) != len(expected) or observed != expected:
        raise ValueError(f"expected 6 unique comparison rows; got {len(rows)}")
    local = [row for row in rows if row["track"] != "coze"]
    pending = [row for row in rows if row["track"] == "coze"]
    if any(not row["actual_answer"] or row["execution_status"] != "completed" for row in local):
        raise ValueError("each local row must link to a completed real run with a saved answer")
    if any(row["actual_answer"] or row["execution_status"] != "待平台实测" for row in pending):
        raise ValueError("Coze rows must remain blank and explicitly pending until platform evidence exists")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    rows = build_rows()
    check_rows(rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(encode(row) for row in rows)
    print(json.dumps({"output": str(args.output), "rows": len(rows), "completed_local_rows": 4, "coze_rows_waiting_for_human": 2}, ensure_ascii=False))


if __name__ == "__main__":
    main()
