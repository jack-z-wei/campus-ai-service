"""Run bounded, auditable DeepSeek judge batches for saved frozen answer traces."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
PRICE_SOURCE = "https://api-docs.deepseek.com/zh-cn/quick_start/pricing/"
INPUT_PRICE_USD_PER_MILLION = 0.30
OUTPUT_PRICE_USD_PER_MILLION = 1.20


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _append_jsonl(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n")


def _safe_item_id(implementation: str, case_id: str, turn_number: int) -> str:
    return f"{implementation}::{case_id}::{turn_number}"


def _normalized_score(value: object, *, nullable: bool = False) -> int | None:
    if nullable and value is None:
        return None
    if isinstance(value, bool) or value not in (0, 1, 2):
        raise ValueError("judge score must be an integer 0, 1, or 2")
    return int(value)


def _parse_judgement(content: str, citation_applicable: bool, unknown_applicable: bool) -> dict:
    try:
        value = json.loads(content)
    except json.JSONDecodeError as error:
        raise ValueError("Judge returned invalid JSON") from error
    if not isinstance(value, dict):
        raise ValueError("Judge result must be a JSON object")
    scores = {
        "correctness": _normalized_score(value.get("correctness")),
        "faithfulness": _normalized_score(value.get("faithfulness")),
        "citation_accuracy": _normalized_score(value.get("citation_accuracy"), nullable=True),
    }
    if not citation_applicable:
        scores["citation_accuracy"] = None
    elif scores["citation_accuracy"] is None:
        raise ValueError("Judge omitted applicable citation score")
    unknown_handled = value.get("unknown_handled")
    if unknown_applicable and not isinstance(unknown_handled, bool):
        raise ValueError("Judge omitted unknown_handled boolean")
    if not unknown_applicable:
        unknown_handled = None
    rationale = value.get("rationale", {})
    if not isinstance(rationale, dict):
        rationale = {}
    return {
        **scores,
        "unknown_handled": unknown_handled,
        "rationale": {key: str(rationale.get(key, ""))[:600] for key in ("correctness", "faithfulness", "citation_accuracy", "unknown_handled")},
    }


def _request_payload(api_key: str, base_url: str, model: str, messages: list[dict], timeout_seconds: float) -> tuple[dict, dict, int]:
    import httpx

    started = time.monotonic()
    response = httpx.post(
        f"{base_url.rstrip('/')}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "messages": messages,
            "temperature": 0,
            "max_tokens": 768,
            "thinking": {"type": "disabled"},
            "response_format": {"type": "json_object"},
            "stream": False,
        },
        timeout=timeout_seconds,
        trust_env=False,
    )
    elapsed_ms = round((time.monotonic() - started) * 1000, 3)
    response.raise_for_status()
    return response.json(), {"http_status": response.status_code}, elapsed_ms


def run_batch(evaluation_run_id: str, item_ids: list[str], timeout_seconds: float) -> int:
    if sys.platform != "win32":
        raise SystemExit("Run answer judges with the Windows project .venv.")
    if not 1 <= len(item_ids) <= 5:
        raise SystemExit("Submit 1 to 5 answer judge items per batch.")
    input_path = ROOT / "runs" / evaluation_run_id / "judge_input.jsonl"
    if not input_path.is_file():
        raise SystemExit(f"Run the metric derivation first: {input_path}")
    dataset = _read_jsonl(input_path)
    indexed = {
        _safe_item_id(row["implementation"], row["case_id"], int(row["turn_number"])): row
        for row in dataset
    }
    unknown_ids = [item_id for item_id in item_ids if item_id not in indexed]
    if unknown_ids:
        raise SystemExit(f"Unknown answer judge item IDs: {unknown_ids}")
    if len(set(item_ids)) != len(item_ids):
        raise SystemExit("Duplicate judge item IDs are not allowed in one batch.")

    eval_dir = input_path.parent
    results_path = eval_dir / "judgements.jsonl"
    old = _read_jsonl(results_path)
    completed = {row["item_id"] for row in old if row.get("status") == "completed"}

    from core import settings

    if not settings.DEEPSEEK_API_KEY:
        raise SystemExit("DEEPSEEK_API_KEY is not configured in the Windows environment.")
    if settings.DEEPSEEK_MODEL != "deepseek-flash":
        raise SystemExit("The judge model is pinned to deepseek-flash.")
    model = settings.DEEPSEEK_MODEL
    api_key = settings.DEEPSEEK_API_KEY.get_secret_value()
    prompt_path = ROOT / "prompts" / "campus_evaluation_judge_v2.md"
    system_prompt = prompt_path.read_text(encoding="utf-8")

    for item_id in item_ids:
        if item_id in completed:
            print(f"skip {item_id}: completed judgement already recorded", flush=True)
            continue
        item = indexed[item_id]
        started_at = datetime.now(ZoneInfo("Asia/Shanghai"))
        prompt_payload = {
            "case_id": item["case_id"],
            "category": item["category"],
            "turn_number": item["turn_number"],
            "question": item.get("question"),
            "turn_specific_criteria": item.get("expected_assistant_criteria"),
            "frozen_answer_points": item.get("expected_answer_points", []),
            "required_caveats": item.get("expected_caveats", []),
            "gold_source_ids": item.get("expected_source_ids", []),
            "retrieved_evidence": item.get("judge_evidence", []),
            "synthetic_tool_results": item.get("tool_results", []),
            "assistant_answer": item.get("answer"),
            "citation_applicable": bool(item.get("expected_source_ids")),
            "unknown_handling_applicable": item.get("category") == "unknown",
        }
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(prompt_payload, ensure_ascii=False)},
        ]
        safe_stem = re.sub(r"[^A-Za-z0-9_-]+", "_", item_id)
        raw_dir = eval_dir / "judge_raw" / safe_stem
        raw_dir.mkdir(parents=True, exist_ok=True)
        attempt = 1
        while (raw_dir / f"attempt-{attempt:02d}.json").exists():
            attempt += 1
        raw_path = raw_dir / f"attempt-{attempt:02d}.json"
        row = {
            "item_id": item_id,
            "implementation": item["implementation"],
            "case_id": item["case_id"],
            "category": item["category"],
            "turn_number": item["turn_number"],
            "attempt": attempt,
            "started_at": started_at.isoformat(timespec="seconds"),
            "judge_model": model,
            "prompt_sha256": hashlib.sha256(prompt_path.read_bytes()).hexdigest(),
            "prompt_version": "campus_evaluation_judge_v2",
            "status": "failed",
            "raw_file": str(raw_path.relative_to(ROOT)).replace("\\", "/"),
        }
        usage_record = None
        try:
            payload, response_meta, elapsed_ms = _request_payload(
                api_key, settings.DEEPSEEK_BASE_URL, model, messages, timeout_seconds
            )
            choice = (payload.get("choices") or [{}])[0]
            message = choice.get("message") or {}
            content = message.get("content")
            if not isinstance(content, str):
                raise ValueError("Judge response content is not text")
            judgement = _parse_judgement(
                content,
                bool(item.get("expected_source_ids")),
                item.get("category") == "unknown",
            )
            usage = payload.get("usage") or {}
            input_tokens = usage.get("prompt_tokens", usage.get("input_tokens"))
            output_tokens = usage.get("completion_tokens", usage.get("output_tokens"))
            usage_available = isinstance(input_tokens, int) and isinstance(output_tokens, int)
            cost = round((input_tokens * INPUT_PRICE_USD_PER_MILLION + output_tokens * OUTPUT_PRICE_USD_PER_MILLION) / 1_000_000, 10) if usage_available else None
            usage_record = {
                "run_id": evaluation_run_id,
                "case_id": item["case_id"],
                "implementation": f"judge_for_{item['implementation']}",
                "provider": "deepseek",
                "model": model,
                "invocation": attempt,
                "request_status": "succeeded",
                "request_attempted": True,
                "usage_available": usage_available,
                "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens} if usage_available else None,
                "estimated_cost_usd": cost,
                "cost_basis": "DeepSeek peak rate; cache miss assumed for all input tokens",
                "pricing_source": PRICE_SOURCE,
            }
            row.update({"status": "completed", "scores": judgement, "elapsed_ms": elapsed_ms, "usage": usage_record.get("usage"), "estimated_cost_usd": cost, "response_id": payload.get("id")})
            raw = {
                "item_id": item_id,
                "attempt": attempt,
                "request_messages": messages,
                "request_options": {"model": model, "temperature": 0, "max_tokens": 768, "thinking": {"type": "disabled"}, "response_format": {"type": "json_object"}},
                "response_metadata": response_meta,
                "response_payload": payload,
                "parsed_scores": judgement,
                "elapsed_ms": elapsed_ms,
            }
        except Exception as error:
            row["error_type"] = type(error).__name__
            raw = {"item_id": item_id, "attempt": attempt, "request_messages": messages, "error_type": type(error).__name__}
        raw_path.write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        row["finished_at"] = datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds")
        _append_jsonl(results_path, row)
        if usage_record is not None:
            _append_jsonl(ROOT / "reports" / "API_USAGE.jsonl", usage_record)
        _append_jsonl(
            ROOT / "reports" / "API_REQUEST_EVENTS.jsonl",
            {"run_id": evaluation_run_id, "event": "answer_judge_request_finished", "case_id": item["case_id"], "implementation": item["implementation"], "turn_number": item["turn_number"], "status": row["status"], "error_type": row.get("error_type"), "latency_ms": row.get("elapsed_ms")},
        )
        print(f"{row['status']} {item_id} judge={model} elapsed={row.get('elapsed_ms', 'n/a')}ms", flush=True)
        if row["status"] == "completed":
            completed.add(item_id)

    latest = {}
    for row in _read_jsonl(results_path):
        latest[row["item_id"]] = row
    requested_results = [latest.get(item_id, {}) for item_id in item_ids]
    return 0 if all(row.get("status") == "completed" for row in requested_results) else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evaluation-run-id", required=True)
    parser.add_argument("--item-ids", nargs="+", required=True, help="IDs in implementation::case::turn format")
    parser.add_argument("--timeout-seconds", type=float, default=45)
    args = parser.parse_args()
    if args.timeout_seconds <= 0:
        parser.error("--timeout-seconds must be positive")
    return run_batch(args.evaluation_run_id, args.item_ids, args.timeout_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
