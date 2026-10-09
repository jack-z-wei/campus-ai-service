"""Run a small real-model RAG batch through the campus Agent on Windows."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[1]
API_USAGE_LOG = PROJECT_ROOT / "reports" / "API_USAGE.jsonl"
INPUT_PRICE_USD_PER_MILLION = 0.30
OUTPUT_PRICE_USD_PER_MILLION = 1.20


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def extract_usage(message) -> dict | None:
    usage = getattr(message, "usage_metadata", None)
    if isinstance(usage, dict) and {"input_tokens", "output_tokens"} <= usage.keys():
        result = {
            "input_tokens": int(usage["input_tokens"]),
            "output_tokens": int(usage["output_tokens"]),
            "total_tokens": int(usage.get("total_tokens", 0)),
        }
    else:
        provider_usage = getattr(message, "response_metadata", {}).get("token_usage")
        if not isinstance(provider_usage, dict):
            return None
        result = {
            "input_tokens": int(provider_usage.get("prompt_tokens", 0)),
            "output_tokens": int(provider_usage.get("completion_tokens", 0)),
            "total_tokens": int(provider_usage.get("total_tokens", 0)),
        }
    return result


def write_api_usage(run_id: str, case_id: str, invocation: int, usage: dict | None) -> dict:
    if usage is None:
        entry = {
            "run_id": run_id,
            "case_id": case_id,
            "model": "deepseek-flash",
            "invocation": invocation,
            "usage_available": False,
            "estimated_cost_usd": None,
        }
    else:
        cost = (
            usage["input_tokens"] * INPUT_PRICE_USD_PER_MILLION
            + usage["output_tokens"] * OUTPUT_PRICE_USD_PER_MILLION
        ) / 1_000_000
        entry = {
            "run_id": run_id,
            "case_id": case_id,
            "model": "deepseek-flash",
            "invocation": invocation,
            "usage_available": True,
            "usage": usage,
            "estimated_cost_usd": round(cost, 10),
            "cost_basis": "DeepSeek peak rate; cache miss assumed for all input tokens",
        }
    with API_USAGE_LOG.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def load_case_map() -> dict:
    data = json.loads(
        (PROJECT_ROOT / "evaluation" / "frozen_cases.json").read_text(encoding="utf-8")
    )
    return {case["case_id"]: case for case in data["cases"]}


def retrieval_metrics(source_ids: list[str], expected_source_ids: list[str]) -> dict:
    unique_sources = list(dict.fromkeys(source_ids))
    relevant = set(expected_source_ids)
    first_rank = next(
        (rank for rank, source in enumerate(unique_sources, start=1) if source in relevant),
        None,
    )
    return {
        f"recall_at_{k}": round(len(set(unique_sources[:k]) & relevant) / len(relevant), 6)
        if relevant
        else None
        for k in (1, 3, 5)
    } | {"mrr_at_5": round(1 / first_rank, 6) if first_rank and first_rank <= 5 else 0.0}


async def run_batch(prompt_version: str, label: str, case_ids: list[str]) -> int:
    if sys.platform != "win32":
        raise SystemExit("Run this batch with the Windows project .venv.")

    sys.path.insert(0, str(PROJECT_ROOT / "src"))
    from langchain_core.messages import HumanMessage, ToolMessage

    from agents import campus_customer_service as campus_agent_module
    from core import get_model, settings
    from schema.models import DeepseekModelName

    if not settings.DEEPSEEK_API_KEY:
        raise SystemExit("DEEPSEEK_API_KEY is not configured in the Windows environment.")
    if DeepseekModelName.DEEPSEEK_FLASH not in settings.AVAILABLE_MODELS:
        raise SystemExit("deepseek-flash is not in the configured model allowlist.")

    prompt_path = PROJECT_ROOT / "prompts" / f"campus_system_{prompt_version}.md"
    prompt_text = prompt_path.read_text(encoding="utf-8")
    cases = load_case_map()
    selected = []
    for case_id in case_ids:
        case = cases.get(case_id)
        if not case or case["category"] not in {"knowledge", "unknown"}:
            raise ValueError(f"{case_id} is not a frozen knowledge/unknown question.")
        if len(case.get("turns", [])) != 1 or case["turns"][0].get("role") != "user":
            raise ValueError(f"{case_id} is not a single-turn case.")
        selected.append(case)

    timestamp = datetime.now().astimezone()
    run_id = timestamp.strftime(f"{label}-{prompt_version}-%Y%m%d-%H%M%S")
    run_dir = PROJECT_ROOT / "runs" / run_id
    (run_dir / "traces").mkdir(parents=True, exist_ok=False)
    index_config = json.loads(
        (PROJECT_ROOT / "data" / "campus" / "index_config.json").read_text(encoding="utf-8")
    )
    frozen_path = PROJECT_ROOT / "evaluation" / "frozen_cases.json"
    manifest = {
        "run_id": run_id,
        "started_at": timestamp.isoformat(timespec="seconds"),
        "mode": "deepseek_live_campus_rag",
        "agent": "campus-customer-service",
        "model": DeepseekModelName.DEEPSEEK_FLASH.value,
        "prompt_version": prompt_version,
        "prompt_sha256": sha256(prompt_path),
        "frozen_cases_sha256": sha256(frozen_path),
        "source_manifest_sha256": index_config["source_manifest_sha256"],
        "index_id": index_config["index_id"],
        "chunking": index_config["chunking"],
        "embedding": index_config["embedding"],
        "search_top_k": 5,
        "configured_max_tokens_per_model_turn": 768,
        "deepseek_thinking_disabled": True,
        "case_ids": case_ids,
        "course_answer_evaluation": True,
        "paid_api_request_attempted": False,
        "case_count": len(selected),
        "completed_case_count": 0,
        "failed_case_count": 0,
    }
    usage_entries: list[dict] = []
    cost_sum = 0.0
    all_case_metrics: list[dict] = []
    per_case_path = run_dir / "per_case.jsonl"
    get_model.cache_clear()

    for case in selected:
        case_id = case["case_id"]
        question = case["turns"][0]["content"]
        trace_id = str(uuid4())
        started = time.monotonic()
        case_result: dict = {
            "run_id": run_id,
            "trace_id": trace_id,
            "case_id": case_id,
            "category": case["category"],
            "question": question,
            "expected_source_ids": case.get("gold", {}).get("source_ids", []),
            "expected_answer_points": case.get("gold", {}).get("answer_points", []),
            "required_caveats": case.get("gold", {}).get("required_caveats", []),
            "forbidden_claims": case.get("gold", {}).get("forbidden_claims", []),
            "tool_results": [],
            "api_invocations": [],
            "status": "running",
        }
        try:
            manifest["paid_api_request_attempted"] = True
            with patch.object(campus_agent_module, "_system_prompt", return_value=prompt_text):
                result = await asyncio.wait_for(
                    campus_agent_module.campus_customer_service.ainvoke(
                        {"messages": [HumanMessage(content=question)]},
                        config={
                            "configurable": {
                                "thread_id": trace_id,
                                "user_id": "campus-rag-eval",
                                "model": DeepseekModelName.DEEPSEEK_FLASH,
                                "simulation_user_id": "SIM-USER-001",
                            },
                            "recursion_limit": 10,
                        },
                    ),
                    timeout=150,
                )
            messages = result["messages"]
            ai_messages = [
                message for message in messages if getattr(message, "type", None) == "ai"
            ]
            tool_messages = [message for message in messages if isinstance(message, ToolMessage)]
            for index, message in enumerate(ai_messages, start=1):
                usage_entry = write_api_usage(run_id, case_id, index, extract_usage(message))
                usage_entries.append(usage_entry)
                case_result["api_invocations"].append(usage_entry)
                if usage_entry.get("estimated_cost_usd") is not None:
                    cost_sum += usage_entry["estimated_cost_usd"]

            tool_payloads = []
            for message in tool_messages:
                if isinstance(message.content, str):
                    try:
                        tool_payloads.append(json.loads(message.content))
                    except json.JSONDecodeError:
                        tool_payloads.append({"unparsed_tool_content": message.content})
                else:
                    tool_payloads.append({"tool_content_type": type(message.content).__name__})
            search_results = [
                payload for payload in tool_payloads if isinstance(payload.get("results"), list)
            ]
            ordered_source_ids = []
            for payload in search_results:
                for item in payload["results"]:
                    source_id = item.get("source_id")
                    if source_id and source_id not in ordered_source_ids:
                        ordered_source_ids.append(source_id)
            answer = next(
                (
                    message.content
                    for message in reversed(ai_messages)
                    if isinstance(message.content, str)
                ),
                "",
            )
            case_result.update(
                {
                    "status": "completed",
                    "model_invocation_count": len(ai_messages),
                    "tool_call_count": sum(len(message.tool_calls) for message in ai_messages),
                    "tool_calls": [
                        {
                            "name": call.get("name"),
                            "args": call.get("args", {}),
                            "id": call.get("id"),
                        }
                        for message in ai_messages
                        for call in message.tool_calls
                    ],
                    "tool_results": tool_payloads,
                    "retrieved_source_ids_by_rank": ordered_source_ids,
                    "retrieval_metrics": retrieval_metrics(
                        ordered_source_ids, case_result["expected_source_ids"]
                    ),
                    "answer": answer,
                    "elapsed_seconds": round(time.monotonic() - started, 3),
                }
            )
            manifest["completed_case_count"] += 1
            all_case_metrics.append(case_result["retrieval_metrics"])
            (run_dir / "traces" / f"{case_id}.json").write_text(
                json.dumps(case_result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            with per_case_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(case_result, ensure_ascii=False) + "\n")
            print(
                f"completed {case_id}: calls={len(ai_messages)}, "
                f"recall@5={case_result['retrieval_metrics']['recall_at_5']}",
                flush=True,
            )
        except Exception as error:
            case_result.update(
                {
                    "status": "failed",
                    "error_type": type(error).__name__,
                    "elapsed_seconds": round(time.monotonic() - started, 3),
                }
            )
            manifest["failed_case_count"] += 1
            with per_case_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(case_result, ensure_ascii=False) + "\n")
            (run_dir / "traces" / f"{case_id}.json").write_text(
                json.dumps(case_result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            print(f"failed {case_id}: {type(error).__name__}", flush=True)

    metric_names = ("recall_at_1", "recall_at_3", "recall_at_5", "mrr_at_5")
    manifest.update(
        {
            "finished_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "api_invocation_count": len(usage_entries),
            "api_usage_values_available": all(
                entry.get("usage_available") for entry in usage_entries
            ),
            "estimated_total_cost_usd": round(cost_sum, 10),
            "retrieval_macro_average": {
                name: round(
                    sum(metric[name] for metric in all_case_metrics) / len(all_case_metrics), 6
                )
                if all_case_metrics
                else None
                for name in metric_names
            },
            "answer_quality_human_review_required": True,
            "limitations": [
                "Answer correctness, faithfulness and citation accuracy are not inferred from retrieval metrics.",
                "Runs use the same frozen questions and current recorded index; no cache result is substituted.",
            ],
        }
    )
    (run_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2), flush=True)
    return 0 if manifest["failed_case_count"] == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt-version", choices=("v1", "v2"), required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--case-ids", nargs="+", required=True)
    args = parser.parse_args()
    return asyncio.run(run_batch(args.prompt_version, args.label, args.case_ids))


if __name__ == "__main__":
    raise SystemExit(main())
