"""Run one frozen single- or multi-turn case through the engineering agent on Windows."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from run_campus_agent_smoke_windows import _token_usage  # noqa: E402
from run_campus_principles_multiturn_windows import _load_case, _tool_contract_result  # noqa: E402

PRICE_SOURCE = "https://api-docs.deepseek.com/zh-cn/quick_start/pricing/"
INPUT_PRICE_USD_PER_MILLION = 0.30
OUTPUT_PRICE_USD_PER_MILLION = 1.20


def _append_jsonl(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def _text(content) -> str:
    if isinstance(content, str):
        return content
    if content is None:
        return ""
    return json.dumps(content, ensure_ascii=False)


def _tool_results(messages) -> list[dict]:
    results = []
    for message in messages:
        if getattr(message, "type", None) != "tool":
            continue
        try:
            value = (
                json.loads(message.content) if isinstance(message.content, str) else message.content
            )
        except (json.JSONDecodeError, TypeError):
            value = {"content_type": type(message.content).__name__}
        results.append(
            {
                "name": getattr(message, "name", None),
                "tool_call_id": getattr(message, "tool_call_id", None),
                "result": value,
            }
        )
    return results


async def _run(case_id: str, timeout_seconds: float) -> int:
    if sys.platform != "win32":
        raise SystemExit("Run this script with the Windows project .venv.")

    from langchain_core.messages import HumanMessage
    from langchain_core.runnables import RunnableConfig
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

    from agents.campus_customer_service import MAX_MEMORY_TURNS, campus_customer_service
    from core import get_model, settings
    from schema.models import DeepseekModelName

    if not settings.DEEPSEEK_API_KEY:
        raise SystemExit("DEEPSEEK_API_KEY is not configured in the Windows environment.")
    if DeepseekModelName.DEEPSEEK_FLASH not in settings.AVAILABLE_MODELS:
        raise SystemExit("deepseek-flash is not in the configured model allowlist.")

    case = _load_case(case_id)
    user_id = case.get("context", {}).get("authenticated_user_id")
    if not case.get("turns"):
        raise SystemExit("The selected frozen case has no turns.")

    started_at = datetime.now(ZoneInfo("Asia/Shanghai"))
    run_id = started_at.strftime("engineering-case-%Y%m%d-%H%M%S-") + uuid4().hex[:8]
    run_dir = PROJECT_ROOT / "runs" / run_id
    trace_dir = run_dir / "traces"
    trace_dir.mkdir(parents=True, exist_ok=False)
    db_path = run_dir / "checkpoints.db"
    thread_id = run_id
    prompt_path = PROJECT_ROOT / "prompts" / "campus_system_v1.md"
    source_manifest_path = PROJECT_ROOT / "docs" / "campus" / "source_manifest.json"
    frozen_cases_path = PROJECT_ROOT / "evaluation" / "frozen_cases.json"
    implementation_paths = [
        PROJECT_ROOT / "src" / "agents" / "campus_customer_service.py",
        PROJECT_ROOT / "src" / "agents" / "campus_tools.py",
        PROJECT_ROOT / "src" / "campus" / "knowledge.py",
        PROJECT_ROOT / "src" / "campus" / "retrieval.py",
        PROJECT_ROOT / "src" / "campus" / "retrieval_chroma.py",
        PROJECT_ROOT / "src" / "campus" / "runtime.py",
        PROJECT_ROOT / "src" / "campus" / "tools" / "status.py",
    ]
    manifest = {
        "run_id": run_id,
        "case_id": case_id,
        "category": case.get("category"),
        "started_at": started_at.isoformat(timespec="seconds"),
        "implementation": "engineering_langgraph_campus_agent",
        "agent": "campus-customer-service",
        "model": DeepseekModelName.DEEPSEEK_FLASH.value,
        "thread_id": thread_id,
        "checkpointer": "upstream_async_sqlite_saver",
        "checkpointer_database": str(db_path.resolve()),
        "simulation_user_id": user_id,
        "bounded_model_context_turns": MAX_MEMORY_TURNS,
        "prompt_sha256": hashlib.sha256(prompt_path.read_bytes()).hexdigest(),
        "source_manifest_sha256": hashlib.sha256(source_manifest_path.read_bytes()).hexdigest(),
        "frozen_cases_sha256": hashlib.sha256(frozen_cases_path.read_bytes()).hexdigest(),
        "implementation_sha256": {
            path.relative_to(PROJECT_ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in implementation_paths
        },
        "max_model_turn_seconds": timeout_seconds,
        "course_case_result": True,
        "synthetic_business_data_only": True,
        "paid_api_request_attempted": False,
        "paid_api_request_performed": False,
        "turn_count_expected": len(case["turns"]),
        "turn_count_completed": 0,
        "estimated_total_cost_usd": None,
        "trace_dir": "traces/",
    }
    (run_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (run_dir / "per_turn.jsonl").write_text("", encoding="utf-8")

    any_request_attempted = False
    any_response_received = False
    total_cost = 0.0
    costs_known = True
    request_count = 0
    completed_turns = 0
    try:
        get_model.cache_clear()
        campus_customer_service.checkpointer = None
        async with AsyncSqliteSaver.from_conn_string(str(db_path)) as checkpointer:
            await checkpointer.setup()
            campus_customer_service.checkpointer = checkpointer
            config = RunnableConfig(
                configurable={
                    "thread_id": thread_id,
                    "user_id": user_id or f"evaluation-{run_id}",
                    "simulation_user_id": user_id,
                    "model": DeepseekModelName.DEEPSEEK_FLASH,
                },
                metadata={
                    "user_id": user_id or f"evaluation-{run_id}",
                    "agent_id": "campus-customer-service",
                },
                recursion_limit=10,
            )
            for turn_number, turn in enumerate(case["turns"], start=1):
                question = turn.get("user") or turn.get("content")
                before = await campus_customer_service.aget_state(config=config)
                prior_messages = list(before.values.get("messages", []))
                from agents.campus_customer_service import recent_messages_for_model

                bounded = recent_messages_for_model(prior_messages)
                current_context_turns = sum(
                    getattr(message, "type", None) == "human" for message in bounded
                )
                any_request_attempted = True
                invocation_started = time.monotonic()
                result = await asyncio.wait_for(
                    campus_customer_service.ainvoke(
                        {"messages": [HumanMessage(content=question)]}, config=config
                    ),
                    timeout=timeout_seconds,
                )
                elapsed_seconds = round(time.monotonic() - invocation_started, 3)
                all_messages = list(result.get("messages", []))
                new_messages = all_messages[len(prior_messages) :]
                ai_messages = [
                    message for message in new_messages if getattr(message, "type", None) == "ai"
                ]
                tool_messages = _tool_results(new_messages)
                actual_calls = [
                    {
                        "name": call.get("name"),
                        "arguments": json.dumps(call.get("args", {}), ensure_ascii=False),
                    }
                    for message in ai_messages
                    for call in getattr(message, "tool_calls", [])
                ]
                answer = next(
                    (
                        _text(message.content)
                        for message in reversed(ai_messages)
                        if not getattr(message, "tool_calls", []) and _text(message.content).strip()
                    ),
                    "",
                )
                status_verified = any(
                    item["result"].get("outcome") == "found" for item in tool_messages
                )
                ticket_verified = any(
                    item["result"].get("outcome") == "created_simulated_ticket"
                    and item["result"].get("simulation_only") is True
                    and item["result"].get("real_human_contacted") is False
                    for item in tool_messages
                )
                model_usage = []
                for invocation, message in enumerate(ai_messages, start=1):
                    usage = _token_usage(message)
                    record = {
                        "run_id": run_id,
                        "case_id": case_id,
                        "turn_number": turn_number,
                        "implementation": "engineering",
                        "provider": "deepseek",
                        "model": DeepseekModelName.DEEPSEEK_FLASH.value,
                        "invocation": invocation,
                        "request_status": "succeeded",
                        "request_attempted": True,
                        "usage_available": usage is not None,
                        "usage": usage,
                        "estimated_cost_usd": (
                            round(
                                (
                                    usage["input_tokens"] * INPUT_PRICE_USD_PER_MILLION
                                    + usage["output_tokens"] * OUTPUT_PRICE_USD_PER_MILLION
                                )
                                / 1_000_000,
                                10,
                            )
                            if usage is not None
                            else None
                        ),
                        "cost_basis": "DeepSeek peak rate; cache miss assumed for all input tokens",
                        "pricing_source": PRICE_SOURCE,
                    }
                    _append_jsonl(PROJECT_ROOT / "reports" / "API_USAGE.jsonl", record)
                    _append_jsonl(
                        PROJECT_ROOT / "reports" / "API_REQUEST_EVENTS.jsonl",
                        {
                            "run_id": run_id,
                            "event": "engineering_case_request_finished",
                            "turn_number": turn_number,
                            "invocation": invocation,
                            "status": "succeeded",
                        },
                    )
                    model_usage.append(record)
                    request_count += 1
                    any_response_received = True
                    if usage is None:
                        costs_known = False
                    else:
                        total_cost += record["estimated_cost_usd"]

                trace = {
                    "run_id": run_id,
                    "case_id": case_id,
                    "turn_number": turn_number,
                    "question": question,
                    "answer": answer,
                    "elapsed_seconds": elapsed_seconds,
                    "memory": {
                        "prior_stored_message_count": len(prior_messages),
                        "model_context_turn_count": current_context_turns,
                        "max_model_context_turns": MAX_MEMORY_TURNS,
                        "thread_id": thread_id,
                    },
                    "new_messages": [
                        {
                            "type": getattr(message, "type", type(message).__name__),
                            "content": _text(message.content),
                            "tool_calls": getattr(message, "tool_calls", []),
                        }
                        for message in new_messages
                    ],
                    "tool_calls": actual_calls,
                    "tool_results": tool_messages,
                    "model_usage": model_usage,
                    "status_tool_verified": status_verified,
                    "ticket_tool_verified": ticket_verified,
                    "status": "completed" if answer else "no_final_answer",
                }
                trace_path = trace_dir / f"turn_{turn_number:02d}.json"
                trace_path.write_text(
                    json.dumps(trace, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
                )
                expected_tool = turn.get("expected_tool", case.get("gold", {}).get("expected_tool"))
                if case.get("category") in {"knowledge", "unknown"}:
                    expected_tool = {
                        "name": "search_campus_knowledge",
                        "arguments": {},
                        "result": "ok_or_no_evidence",
                    }
                per_turn = {
                    "run_id": run_id,
                    "case_id": case_id,
                    "turn_number": turn_number,
                    "question": question,
                    "expected_assistant_criteria": turn.get("expected_assistant_criteria"),
                    "expected_answer_points": case.get("gold", {}).get("answer_points", []),
                    "expected_caveats": case.get("gold", {}).get("required_caveats", []),
                    "expected_tool": expected_tool,
                    "answer": answer,
                    "status": trace["status"],
                    "tool_contract": _tool_contract_result(
                        expected_tool,
                        actual_calls,
                        simulation_user_id=user_id,
                    ),
                    "status_tool_verified": status_verified,
                    "ticket_tool_verified": ticket_verified,
                    "memory": trace["memory"],
                    "trace_file": f"traces/{trace_path.name}",
                }
                _append_jsonl(run_dir / "per_turn.jsonl", per_turn)
                manifest["turn_count_completed"] = turn_number if answer else turn_number - 1
                manifest["paid_api_request_attempted"] = any_request_attempted
                manifest["paid_api_request_performed"] = any_response_received
                manifest["model_request_count"] = request_count
                manifest["estimated_total_cost_usd"] = (
                    round(total_cost, 10) if costs_known else None
                )
                (run_dir / "manifest.json").write_text(
                    json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
                )
                if not answer:
                    break
                completed_turns += 1
            await campus_customer_service.checkpointer.adelete_thread(thread_id)
            campus_customer_service.checkpointer = None
        manifest.update(
            {
                "status": "completed" if completed_turns == len(case["turns"]) else "incomplete",
                "paid_api_request_attempted": any_request_attempted,
                "paid_api_request_performed": any_response_received,
                "model_request_count": request_count,
                "turn_count_completed": completed_turns,
                "estimated_total_cost_usd": round(total_cost, 10) if costs_known else None,
                "checkpoint_thread_deleted_after_run": True,
            }
        )
    except Exception as error:
        manifest.update(
            {
                "status": "failed",
                "error_type": type(error).__name__,
                "paid_api_request_attempted": any_request_attempted,
                "paid_api_request_performed": any_response_received
                if any_response_received
                else None
                if any_request_attempted
                else False,
                "model_request_count": request_count,
                "turn_count_completed": completed_turns,
                "estimated_total_cost_usd": round(total_cost, 10) if costs_known else None,
            }
        )
        (run_dir / "execution.log").write_text(
            f"{type(error).__name__}: {error}\n", encoding="utf-8"
        )
        if getattr(campus_customer_service, "checkpointer", None) is not None:
            campus_customer_service.checkpointer = None
    finally:
        manifest["finished_at"] = datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(
            timespec="seconds"
        )
        (run_dir / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    print(
        json.dumps(
            {
                "run_id": run_id,
                "case_id": case_id,
                "status": manifest.get("status"),
                "turn_count_completed": manifest.get("turn_count_completed"),
                "model_request_count": manifest.get("model_request_count", 0),
                "estimated_total_cost_usd": manifest.get("estimated_total_cost_usd"),
                "manifest": str(run_dir / "manifest.json"),
                "per_turn": str(run_dir / "per_turn.jsonl"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if manifest.get("status") == "completed" else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--timeout-seconds", type=float, default=120.0)
    args = parser.parse_args()
    if args.timeout_seconds <= 0:
        parser.error("--timeout-seconds must be positive")
    return asyncio.run(_run(args.case_id, args.timeout_seconds))


if __name__ == "__main__":
    raise SystemExit(main())
