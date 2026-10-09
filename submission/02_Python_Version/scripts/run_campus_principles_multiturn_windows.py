"""Run one frozen two-turn campus case through the principles Agent on Windows."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from run_campus_principles_windows import (  # noqa: E402
    PRICE_SOURCE,
    append_jsonl,
    summarize_usage,
)


def _load_case(case_id: str) -> dict:
    frozen = json.loads((ROOT / "evaluation" / "frozen_cases.json").read_text(encoding="utf-8"))
    for item in frozen["cases"]:
        if item["case_id"] == case_id:
            return item
    raise ValueError(f"Unknown frozen case: {case_id}")


def _tool_arguments(trace_tool: dict) -> dict:
    try:
        parsed = json.loads(trace_tool.get("arguments", "{}"))
    except (TypeError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _tool_contract_result(
    expected: dict | None, actual_tools: list[dict], *, simulation_user_id: str
) -> dict:
    expected_tools = [] if expected is None else [expected]
    actual = [
        {"name": item.get("name"), "arguments": _tool_arguments(item)} for item in actual_tools
    ]
    if not expected_tools:
        return {
            "expected_no_tool": True,
            "actual_tool_count": len(actual),
            "tool_selection_match": not actual,
            "argument_match": not actual,
        }
    matches = [
        item for item in actual if item["name"] == expected_tools[0].get("name")
    ]
    expected_arguments = expected_tools[0].get("arguments", {})
    expected_identity = expected_arguments.get("requester_user_id")
    identity_match = (
        expected_identity == simulation_user_id if expected_identity is not None else None
    )
    tool_arguments = {
        key: value for key, value in expected_arguments.items() if key != "requester_user_id"
    }
    argument_match = bool(matches) and all(
        matches[0]["arguments"].get(key) == value
        for key, value in tool_arguments.items()
    )
    return {
        "expected_no_tool": False,
        "expected": expected_tools[0],
        "actual": actual,
        "tool_selection_match": bool(matches),
        "argument_match": argument_match,
        "trusted_identity_match": identity_match,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-id", required=True, choices=("M01", "M02"))
    parser.add_argument("--prompt-version", choices=("v1", "v2"), default="v1")
    parser.add_argument("--top-k", choices=(1, 3, 5), type=int, default=5)
    parser.add_argument(
        "--memory-db",
        type=Path,
        help="Principles memory SQLite path (default: runs/principles_memory.sqlite3).",
    )
    args = parser.parse_args()
    if sys.platform != "win32":
        raise SystemExit("Run the principles multi-turn CLI with the Windows project .venv.")

    case = _load_case(args.case_id)
    if case.get("category") != "multi_turn" or len(case.get("turns", [])) < 2:
        raise SystemExit("The selected frozen case is not a multi-turn conversation.")
    user_id = case.get("context", {}).get("authenticated_user_id")
    if not case.get("context", {}).get("simulation_only") or not user_id:
        raise SystemExit("This runner accepts only cases with explicit synthetic identities.")

    timestamp = datetime.now(ZoneInfo("Asia/Shanghai"))
    run_id = timestamp.strftime("principles-multiturn-%Y%m%d-%H%M%S-") + uuid4().hex[:8]
    session_id = run_id
    run_dir = ROOT / "runs" / run_id
    trace_dir = run_dir / "traces"
    trace_dir.mkdir(parents=True, exist_ok=False)
    memory_path = args.memory_db or ROOT / "runs" / "principles_memory.sqlite3"
    prompt_path = ROOT / "prompts" / f"campus_system_{args.prompt_version}.md"
    frozen_path = ROOT / "evaluation" / "frozen_cases.json"
    source_manifest_path = ROOT / "docs" / "campus" / "source_manifest.json"
    implementation = [
        ROOT / "src" / "campus" / "principle_agent.py",
        ROOT / "src" / "campus" / "principle_tools.py",
        ROOT / "src" / "campus" / "conversation_memory.py",
        ROOT / "src" / "campus" / "runtime.py",
    ]
    manifest = {
        "run_id": run_id,
        "case_id": args.case_id,
        "category": "multi_turn",
        "started_at": timestamp.isoformat(timespec="seconds"),
        "implementation": "principles_python_numpy_httpx_tool_registry",
        "session_id": session_id,
        "memory_db": str(memory_path.resolve()),
        "memory_max_turns": 4,
        "simulation_user_id": user_id,
        "prompt_version": args.prompt_version,
        "prompt_sha256": hashlib.sha256(prompt_path.read_bytes()).hexdigest(),
        "frozen_cases_sha256": hashlib.sha256(frozen_path.read_bytes()).hexdigest(),
        "source_manifest_sha256": hashlib.sha256(source_manifest_path.read_bytes()).hexdigest(),
        "implementation_sha256": {
            f"{path.parent.name}/{path.name}": hashlib.sha256(path.read_bytes()).hexdigest()
            for path in implementation
        },
        "chat_model": None,
        "top_k": args.top_k,
        "paid_api_request_attempted": False,
        "paid_api_request_performed": False,
        "synthetic_business_data_only": True,
        "turn_count_expected": len(case["turns"]),
        "turn_count_completed": 0,
        "estimated_total_cost_usd": None,
        "trace_dir": "traces/",
        "per_turn_file": "per_turn.jsonl",
    }
    (run_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    try:
        from campus.conversation_memory import PrincipleConversationMemory
        from campus.principle_agent import PrincipleAgent
        from campus.runtime import get_campus_status_tools, get_principle_knowledge_search
        from core import settings

        if not settings.DEEPSEEK_API_KEY:
            raise RuntimeError("DEEPSEEK_API_KEY is not configured; no chat request was made.")
        if settings.DEEPSEEK_MODEL != "deepseek-flash":
            raise RuntimeError("The principles run is pinned to deepseek-flash.")

        memory = PrincipleConversationMemory(memory_path)
        agent = PrincipleAgent(
            knowledge_search=get_principle_knowledge_search(),
            status_tools=get_campus_status_tools(),
            api_key=settings.DEEPSEEK_API_KEY.get_secret_value(),
            base_url=settings.DEEPSEEK_BASE_URL,
            model=settings.DEEPSEEK_MODEL,
            prompt=prompt_path.read_text(encoding="utf-8"),
        )
        manifest.update(
            {
                "chat_model": settings.DEEPSEEK_MODEL,
                "price_source": PRICE_SOURCE,
                "cost_estimate_basis": "DeepSeek peak rate; all prompt tokens assumed uncached.",
            }
        )
        completed_turns = 0
        total_cost = 0.0
        costs_known = True
        request_count = 0
        any_request_attempted = False
        any_request_succeeded = False
        (run_dir / "per_turn.jsonl").write_text("", encoding="utf-8")
        for turn_number, turn in enumerate(case["turns"], start=1):
            question = turn.get("user") or turn.get("content")
            history = memory.history(session_id, user_id)
            request_id = f"{run_id}-turn-{turn_number}"
            trace = agent.run(
                question,
                authenticated_user_id=user_id,
                request_id=request_id,
                top_k=args.top_k,
                conversation_history=history,
            )
            if trace.get("status") == "completed":
                kept_turns = memory.append_turn(
                    session_id,
                    user_id,
                    user_message=question,
                    assistant_message=trace.get("answer", ""),
                )
                trace["memory"].update({"stored": True, "stored_turn_count": kept_turns})
                completed_turns += 1
            else:
                trace["memory"].update({"stored": False})

            trace_path = trace_dir / f"turn_{turn_number:02d}.json"
            trace_path.write_text(
                json.dumps(trace, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            contract = _tool_contract_result(
                turn.get("expected_tool"),
                trace.get("tool_calls", []),
                simulation_user_id=user_id,
            )
            per_turn = {
                "run_id": run_id,
                "case_id": args.case_id,
                "turn_number": turn_number,
                "question": question,
                "expected_assistant_criteria": turn.get("expected_assistant_criteria"),
                "answer": trace.get("answer"),
                "status": trace.get("status"),
                "tool_contract": contract,
                "memory": trace.get("memory"),
                "trace_file": f"traces/{trace_path.name}",
            }
            append_jsonl(run_dir / "per_turn.jsonl", per_turn)
            for invocation, request in enumerate(trace.get("model_requests", []), start=1):
                request_count += 1
                any_request_attempted = any_request_attempted or bool(
                    request.get("request_attempted")
                )
                any_request_succeeded = any_request_succeeded or request.get("status") == "succeeded"
                usage_summary, cost = summarize_usage(request.get("usage"))
                append_jsonl(
                    ROOT / "reports" / "API_USAGE.jsonl",
                    {
                        "run_id": run_id,
                        "case_id": args.case_id,
                        "turn_number": turn_number,
                        "implementation": "principles",
                        "provider": "deepseek",
                        "model": settings.DEEPSEEK_MODEL,
                        "invocation": invocation,
                        "request_status": request.get("status"),
                        "request_attempted": request.get("request_attempted", False),
                        **usage_summary,
                        "estimated_cost_usd": cost,
                        "cost_basis": "DeepSeek peak rate; cache miss assumed for all input tokens",
                        "pricing_source": PRICE_SOURCE,
                    },
                )
                append_jsonl(
                    ROOT / "reports" / "API_REQUEST_EVENTS.jsonl",
                    {
                        "run_id": run_id,
                        "event": "principles_multiturn_request_finished",
                        "turn_number": turn_number,
                        "invocation": invocation,
                        "status": request.get("status"),
                        "latency_ms": request.get("latency_ms"),
                        "error_type": request.get("error_type"),
                        "http_status": request.get("http_status"),
                    },
                )
                if cost is None:
                    costs_known = False
                else:
                    total_cost += cost
            manifest["paid_api_request_attempted"] = any_request_attempted
            manifest["paid_api_request_performed"] = (
                True
                if any_request_succeeded
                else None
                if any_request_attempted
                else False
            )
            manifest["model_request_count"] = request_count
            manifest["turn_count_completed"] = completed_turns
            manifest["estimated_total_cost_usd"] = (
                round(total_cost, 10) if costs_known else None
            )
            if trace.get("status") != "completed":
                break

        manifest.update(
            {
                "status": "completed" if completed_turns == len(case["turns"]) else "incomplete",
                "paid_api_request_attempted": any_request_attempted,
                "paid_api_request_performed": (
                    True
                    if any_request_succeeded
                    else None
                    if any_request_attempted
                    else False
                ),
                "model_request_count": request_count,
                "turn_count_completed": completed_turns,
                "estimated_total_cost_usd": round(total_cost, 10) if costs_known else None,
            }
        )
    except Exception as error:
        manifest.update(
            {
                "status": "failed",
                "error_type": type(error).__name__,
                "paid_api_request_performed": None
                if manifest["paid_api_request_attempted"]
                else False,
            }
        )
        (run_dir / "execution.log").write_text(
            f"{type(error).__name__}: {error}\n", encoding="utf-8"
        )
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
                "case_id": args.case_id,
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


if __name__ == "__main__":
    raise SystemExit(main())
