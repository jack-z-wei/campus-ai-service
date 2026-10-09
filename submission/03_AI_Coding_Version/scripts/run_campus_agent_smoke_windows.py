"""Make one bounded, real DeepSeek call through the campus Agent graph on Windows."""

from __future__ import annotations

import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[1]
API_USAGE_LOG = PROJECT_ROOT / "reports" / "API_USAGE.jsonl"
INPUT_PRICE_USD_PER_MILLION = 0.30
OUTPUT_PRICE_USD_PER_MILLION = 1.20


def _token_usage(message) -> dict | None:
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
    details = getattr(message, "response_metadata", {}).get("token_usage", {})
    completion_details = details.get("completion_tokens_details", {})
    reasoning_tokens = completion_details.get("reasoning_tokens")
    if reasoning_tokens is not None:
        result["reasoning_tokens"] = int(reasoning_tokens)
    return result


def _append_usage(run_id: str, model: str, invocation: int, usage: dict | None) -> dict:
    if usage is None:
        entry = {
            "run_id": run_id,
            "model": model,
            "invocation": invocation,
            "usage_available": False,
            "estimated_cost_usd": None,
            "cost_basis": "DeepSeek peak rate; cache miss assumed when usage is present",
        }
    else:
        cost = (
            usage["input_tokens"] * INPUT_PRICE_USD_PER_MILLION
            + usage["output_tokens"] * OUTPUT_PRICE_USD_PER_MILLION
        ) / 1_000_000
        entry = {
            "run_id": run_id,
            "model": model,
            "invocation": invocation,
            "usage_available": True,
            "usage": usage,
            "estimated_cost_usd": round(cost, 10),
            "cost_basis": "DeepSeek peak rate; cache miss assumed for all input tokens",
        }
    with API_USAGE_LOG.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


async def _run() -> int:
    if sys.platform != "win32":
        raise SystemExit("Run this script with the Windows project .venv.")

    sys.path.insert(0, str(PROJECT_ROOT / "src"))
    from langchain_core.messages import HumanMessage, ToolMessage

    from core import get_model, settings
    from schema.models import DeepseekModelName

    if not settings.DEEPSEEK_API_KEY:
        raise SystemExit("DEEPSEEK_API_KEY is not configured in the Windows environment.")
    if DeepseekModelName.DEEPSEEK_FLASH not in settings.AVAILABLE_MODELS:
        raise SystemExit("deepseek-flash is not in the configured model allowlist.")

    from agents.campus_customer_service import campus_customer_service

    now = datetime.now().astimezone()
    run_id = now.strftime("campus-agent-smoke-%Y%m%d-%H%M%S")
    run_dir = PROJECT_ROOT / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    thread_id = str(uuid4())
    question = "请查询我的模拟助学申请记录 SIM-REC-001，告诉我状态和更新时间。"
    manifest: dict = {
        "run_id": run_id,
        "started_at": now.isoformat(timespec="seconds"),
        "mode": "deepseek_live_synthetic_tool_call",
        "agent": "campus-customer-service",
        "model": DeepseekModelName.DEEPSEEK_FLASH.value,
        "question": question,
        "simulation_user_id": "SIM-USER-001",
        "thread_id": thread_id,
        "course_answer_evaluation": False,
        "synthetic_data_only": True,
        "paid_api_request_performed": None,
        "api_request_attempted": False,
        "configured_model_max_tokens": 768,
        "deepseek_thinking_disabled": True,
    }
    started = time.monotonic()
    try:
        get_model.cache_clear()
        manifest["api_request_attempted"] = True
        result = await asyncio.wait_for(
            campus_customer_service.ainvoke(
                {"messages": [HumanMessage(content=question)]},
                config={
                    "configurable": {
                        "thread_id": thread_id,
                        "user_id": "campus-smoke-demo",
                        "model": DeepseekModelName.DEEPSEEK_FLASH,
                        "simulation_user_id": "SIM-USER-001",
                    },
                    "recursion_limit": 10,
                },
            ),
            timeout=120,
        )

        messages = result["messages"]
        ai_messages = [message for message in messages if getattr(message, "type", None) == "ai"]
        tool_messages = [message for message in messages if isinstance(message, ToolMessage)]
        usage_entries = [
            _append_usage(
                run_id,
                DeepseekModelName.DEEPSEEK_FLASH.value,
                index,
                _token_usage(message),
            )
            for index, message in enumerate(ai_messages, start=1)
        ]
        tool_results = []
        for message in tool_messages:
            try:
                tool_results.append(json.loads(message.content))
            except (json.JSONDecodeError, TypeError):
                tool_results.append({"content_type": type(message.content).__name__})

        assistant_text = next(
            (
                message.content
                for message in reversed(ai_messages)
                if isinstance(message.content, str)
            ),
            "",
        )
        status_verified = any(
            item.get("outcome") == "found"
            and item.get("record_id") == "SIM-REC-001"
            and item.get("status") == "材料审核中"
            and item.get("simulation_only") is True
            for item in tool_results
        )
        manifest.update(
            {
                "paid_api_request_performed": True,
                "model_invocation_count": len(ai_messages),
                "usage_entries": usage_entries,
                "tool_calls": [
                    {
                        "name": call.get("name"),
                        "args": call.get("args", {}),
                    }
                    for message in ai_messages
                    for call in getattr(message, "tool_calls", [])
                ],
                "tool_results": tool_results,
                "synthetic_status_tool_verified": status_verified,
                "assistant_answer": assistant_text,
                "assistant_answer_output_tokens": [
                    entry["usage"].get("output_tokens")
                    for entry in usage_entries
                    if entry.get("usage_available")
                ],
                "api_usage_recorded": len(usage_entries) == len(ai_messages),
                "all_usage_values_available": all(
                    entry.get("usage_available") for entry in usage_entries
                ),
            }
        )
        if not status_verified:
            manifest["result"] = (
                "The model did not return the expected synthetic status tool result."
            )
        else:
            manifest["result"] = "Verified synthetic status-tool call and response."
    except Exception as error:
        manifest["error_type"] = type(error).__name__
        manifest["result"] = "Real model integration call failed; no answer result is claimed."
    finally:
        manifest["elapsed_seconds"] = round(time.monotonic() - started, 3)
        manifest["finished_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
        (run_dir / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0 if manifest.get("synthetic_status_tool_verified") else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_run()))
