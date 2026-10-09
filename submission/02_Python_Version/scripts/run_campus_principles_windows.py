"""Run one auditable principles-edition RAG/Agent request on Windows."""

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

INPUT_PRICE_USD_PER_MILLION = 0.30
OUTPUT_PRICE_USD_PER_MILLION = 1.20
PRICE_SOURCE = "https://api-docs.deepseek.com/zh-cn/quick_start/pricing/"


def append_jsonl(path: Path, item: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n")


def load_case(case_id: str) -> dict:
    frozen = json.loads((ROOT / "evaluation" / "frozen_cases.json").read_text(encoding="utf-8"))
    for case in frozen["cases"]:
        if case["case_id"] == case_id:
            if len(case.get("turns", [])) != 1:
                raise ValueError("The one-request principles CLI accepts single-turn frozen cases only.")
            return case
    raise ValueError(f"Unknown frozen case: {case_id}")


def summarize_usage(usage: dict | None) -> tuple[dict, float | None]:
    if not isinstance(usage, dict):
        return {"usage_available": False, "usage": None}, None
    input_tokens = usage.get("input_tokens")
    output_tokens = usage.get("output_tokens")
    available = isinstance(input_tokens, int) and isinstance(output_tokens, int)
    cost = None
    if available:
        cost = round(
            (
                input_tokens * INPUT_PRICE_USD_PER_MILLION
                + output_tokens * OUTPUT_PRICE_USD_PER_MILLION
            )
            / 1_000_000,
            10,
        )
    return {"usage_available": available, "usage": usage}, cost


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    question_group = parser.add_mutually_exclusive_group(required=True)
    question_group.add_argument("--question", help="One campus question; max 1200 characters.")
    question_group.add_argument("--case-id", help="One single-turn ID from the frozen test set.")
    parser.add_argument(
        "--simulation-user-id",
        choices=("SIM-USER-001", "SIM-USER-002", "SIM-USER-003"),
        help="Synthetic demo identity. Never a real authentication credential.",
    )
    parser.add_argument("--request-id", help="Stable request ID for safe ticket replay tests.")
    parser.add_argument("--session-id", help="Persist this run in the bounded principles memory.")
    parser.add_argument(
        "--memory-db",
        type=Path,
        help="Principles memory SQLite path (default: runs/principles_memory.sqlite3).",
    )
    parser.add_argument("--prompt-version", choices=("v1", "v2"), default="v1")
    parser.add_argument("--top-k", choices=(1, 3, 5), type=int, default=5)
    parser.add_argument(
        "--retrieval-only",
        action="store_true",
        help="Run real Ollama embedding and NumPy retrieval without calling any chat API.",
    )
    args = parser.parse_args()

    if sys.platform != "win32":
        raise SystemExit("Run the principles CLI with the Windows project .venv.")

    case = load_case(args.case_id) if args.case_id else None
    question = case["turns"][0]["content"] if case else args.question
    if not isinstance(question, str) or not question.strip() or len(question) > 1200:
        raise SystemExit("Question must contain between 1 and 1200 characters.")
    if args.retrieval_only and args.session_id:
        raise SystemExit("--session-id requires a completed chat run; it cannot be used with --retrieval-only.")
    expected_user = case.get("context", {}).get("authenticated_user_id") if case else None
    if case and args.simulation_user_id and args.simulation_user_id != expected_user:
        raise SystemExit("Selected SIM identity differs from this frozen case context.")
    simulation_user_id = expected_user or args.simulation_user_id
    request_id = args.request_id or f"principles-{uuid4()}"

    timestamp = datetime.now(ZoneInfo("Asia/Shanghai"))
    run_id = timestamp.strftime("principles-%Y%m%d-%H%M%S-") + uuid4().hex[:8]
    run_dir = ROOT / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    prompt_path = ROOT / "prompts" / f"campus_system_{args.prompt_version}.md"
    source_manifest = ROOT / "docs" / "campus" / "source_manifest.json"
    frozen_path = ROOT / "evaluation" / "frozen_cases.json"
    index_config = json.loads((ROOT / "data" / "campus" / "index_config.json").read_text(encoding="utf-8"))
    implementation_files = (
        ROOT / "src" / "campus" / "principle_agent.py",
        ROOT / "src" / "campus" / "principle_tools.py",
        ROOT / "src" / "campus" / "runtime.py",
    )
    manifest = {
        "run_id": run_id,
        "started_at": timestamp.isoformat(timespec="seconds"),
        "implementation": "principles_python_numpy_httpx_tool_registry",
        "case_id": args.case_id,
        "category": case.get("category") if case else None,
        "question": question,
        "simulation_user_id": simulation_user_id,
        "request_id": request_id,
        "prompt_version": args.prompt_version,
        "prompt_sha256": hashlib.sha256(prompt_path.read_bytes()).hexdigest(),
        "implementation_sha256": {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in implementation_files
        },
        "source_manifest_sha256": hashlib.sha256(source_manifest.read_bytes()).hexdigest(),
        "frozen_cases_sha256": hashlib.sha256(frozen_path.read_bytes()).hexdigest(),
        "index_id": index_config["index_id"],
        "embedding": index_config["embedding"],
        "vector_backend": "numpy_cosine",
        "top_k": args.top_k,
        "chat_model": None,
        "configured_max_output_tokens": 768,
        "paid_api_request_attempted": False,
        "paid_api_request_performed": False,
        "course_case_result": case is not None and not args.retrieval_only,
        "retrieval_case_result": case is not None and args.retrieval_only,
        "synthetic_business_data_only": True,
        "answer": None,
        "trace_file": "trace.json",
        "error_type": None,
    }
    (run_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    try:
        from campus.runtime import get_principle_knowledge_search

        search = get_principle_knowledge_search()
        if args.retrieval_only:
            from campus.context_expansion import expand_top_hit_continuation

            result = search.search(question, top_k=args.top_k)
            evidence, context_expansions = expand_top_hit_continuation(
                result.hits, search.chunks
            )
            trace = {
                "question": question,
                "backend": result.backend,
                "top_k": args.top_k,
                "context_expansions": context_expansions,
                "hits": [
                    {
                        "retrieval_rank": item.retrieval_rank,
                        "score": (
                            round(item.cosine_score, 6)
                            if item.cosine_score is not None
                            else None
                        ),
                        "source_id": item.chunk.source_id,
                        "title": item.chunk.metadata.get("title"),
                        "url": item.chunk.metadata.get("url"),
                        "published_on": item.chunk.metadata.get("published_on"),
                        "scope": item.chunk.metadata.get("scope"),
                        "context_expansion": item.chunk.metadata.get("context_expansion"),
                        "text": item.chunk.text,
                    }
                    for item in evidence
                ],
                "paid_api_request_attempted": False,
            }
            manifest.update(
                {
                    "status": "retrieval_only_complete",
                    "answer": None,
                    "paid_api_request_attempted": False,
                    "paid_api_request_performed": False,
                }
            )
        else:
            from campus.principle_agent import PrincipleAgent
            from campus.runtime import get_campus_status_tools
            from core import settings

            if not settings.DEEPSEEK_API_KEY:
                raise RuntimeError("DEEPSEEK_API_KEY is not configured; no chat request was made.")
            if settings.DEEPSEEK_MODEL != "deepseek-flash":
                raise RuntimeError("The principles run is pinned to deepseek-flash.")
            prompt_text = prompt_path.read_text(encoding="utf-8")
            agent = PrincipleAgent(
                knowledge_search=search,
                status_tools=get_campus_status_tools(),
                api_key=settings.DEEPSEEK_API_KEY.get_secret_value(),
                base_url=settings.DEEPSEEK_BASE_URL,
                model=settings.DEEPSEEK_MODEL,
                prompt=prompt_text,
            )
            conversation_memory = None
            conversation_history = []
            if args.session_id:
                from campus.conversation_memory import PrincipleConversationMemory

                conversation_memory = PrincipleConversationMemory(
                    args.memory_db
                    or ROOT / "runs" / "principles_memory.sqlite3"
                )
                conversation_history = conversation_memory.history(
                    args.session_id, simulation_user_id
                )
            manifest.update(
                {
                    "chat_model": settings.DEEPSEEK_MODEL,
                    "paid_api_request_attempted": True,
                    "price_source": PRICE_SOURCE,
                    "cost_estimate_basis": "DeepSeek peak rate; all prompt tokens assumed uncached.",
                    "conversation_memory_enabled": conversation_memory is not None,
                    "session_id": args.session_id,
                    "prior_memory_turns": len(conversation_history) // 2,
                }
            )
            trace = agent.run(
                question,
                authenticated_user_id=simulation_user_id,
                request_id=request_id,
                top_k=args.top_k,
                conversation_history=conversation_history,
            )
            if conversation_memory is not None and trace.get("status") == "completed":
                trace["memory"]["stored_turn_count"] = conversation_memory.append_turn(
                    args.session_id,
                    simulation_user_id,
                    user_message=question,
                    assistant_message=trace.get("answer", ""),
                )
                trace["memory"]["stored"] = True
            elif conversation_memory is not None:
                trace["memory"]["stored"] = False
            model_requests = trace.get("model_requests", [])
            usage_records = []
            total_cost = 0.0
            all_costs_known = bool(model_requests)
            for invocation, request in enumerate(model_requests, start=1):
                request_usage, cost = summarize_usage(request.get("usage"))
                record = {
                    "run_id": run_id,
                    "case_id": args.case_id,
                    "implementation": "principles",
                    "provider": "deepseek",
                    "model": settings.DEEPSEEK_MODEL,
                    "invocation": invocation,
                    "request_status": request.get("status"),
                    "request_attempted": request.get("request_attempted", False),
                    **request_usage,
                    "estimated_cost_usd": cost,
                    "cost_basis": "DeepSeek peak rate; cache miss assumed for all input tokens",
                    "pricing_source": PRICE_SOURCE,
                }
                append_jsonl(ROOT / "reports" / "API_USAGE.jsonl", record)
                append_jsonl(
                    ROOT / "reports" / "API_REQUEST_EVENTS.jsonl",
                    {
                        "run_id": run_id,
                        "event": "principles_request_finished",
                        "invocation": invocation,
                        "status": request.get("status"),
                        "latency_ms": request.get("latency_ms"),
                        "error_type": request.get("error_type"),
                        "http_status": request.get("http_status"),
                    },
                )
                usage_records.append(record)
                if cost is None:
                    all_costs_known = False
                else:
                    total_cost += cost

            manifest.update(
                {
                    "status": trace.get("status"),
                    "paid_api_request_attempted": any(
                        item.get("request_attempted") for item in model_requests
                    ),
                    "paid_api_request_performed": (
                        True
                        if any(item.get("status") == "succeeded" for item in model_requests)
                        else None
                        if any(item.get("request_attempted") for item in model_requests)
                        else False
                    ),
                    "model_request_count": len(model_requests),
                    "api_usage_records": usage_records,
                    "estimated_total_cost_usd": round(total_cost, 10) if all_costs_known else None,
                    "answer": trace.get("answer"),
                    "tool_call_count": trace.get("total_tool_calls"),
                    "tool_names": [item.get("name") for item in trace.get("tool_calls", [])],
                    "registered_tool_names": [
                        item["function"]["name"] for item in agent.registry.definitions
                    ],
                }
            )
    except Exception as error:
        trace = {
            "status": "failed",
            "error_type": type(error).__name__,
            "message": "Principles run failed; no unverified answer is claimed.",
        }
        manifest.update(
            {
                "status": "failed",
                "error_type": type(error).__name__,
                "answer": None,
                "paid_api_request_performed": None
                if manifest["paid_api_request_attempted"]
                else False,
            }
        )
    finally:
        manifest["finished_at"] = datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(
            timespec="seconds"
        )
        (run_dir / "trace.json").write_text(
            json.dumps(trace, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        (run_dir / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    print(
        json.dumps(
            {
                "run_id": run_id,
                "status": manifest.get("status"),
                "case_id": args.case_id,
                "implementation": manifest["implementation"],
                "paid_api_request_attempted": manifest["paid_api_request_attempted"],
                "paid_api_request_performed": manifest["paid_api_request_performed"],
                "model_request_count": manifest.get("model_request_count", 0),
                "estimated_total_cost_usd": manifest.get("estimated_total_cost_usd"),
                "answer": manifest.get("answer"),
                "error_type": manifest.get("error_type"),
                "manifest": str(run_dir / "manifest.json"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if manifest.get("status") in {"completed", "retrieval_only_complete"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
