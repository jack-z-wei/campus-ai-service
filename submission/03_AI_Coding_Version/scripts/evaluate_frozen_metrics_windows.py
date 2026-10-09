"""Recompute frozen-set Retrieval, Agent, and Engineering metrics from saved traces."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from campus.evaluation_metrics import (  # noqa: E402
    average,
    nearest_rank_percentile,
    retrieval_metrics,
    task_tool_process_completed,
    tool_contract,
    unique_source_ids,
)

RUN_IDS = {
    "principles": "baseline-principles-v1-20261006",
    "engineering": "baseline-engineering-v1-20261006",
}
IMPLEMENTATIONS = ("principles", "engineering")


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def _json_arguments(value: object) -> dict:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _expected_tool(implementation: str, case: dict, turn: dict) -> dict | None:
    expected = turn.get("expected_tool", case.get("gold", {}).get("expected_tool"))
    if implementation == "engineering" and case.get("category") in {"knowledge", "unknown"}:
        return {
            "name": "search_campus_knowledge",
            "arguments": {},
            "result": "ok_or_no_evidence",
        }
    return expected


def _normalize_tool_calls(trace: dict) -> list[dict]:
    calls = []
    for item in trace.get("tool_calls", []):
        calls.append(
            {"name": item.get("name"), "arguments": _json_arguments(item.get("arguments"))}
        )
    return calls


def _tool_results(trace: dict) -> list[dict]:
    results = []
    for item in trace.get("tool_calls", []):
        value = item.get("result")
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                value = None
        if isinstance(value, dict):
            results.append({"name": item.get("name"), "result": value})
    for item in trace.get("tool_results", []):
        value = item.get("result")
        if isinstance(value, dict):
            results.append({"name": item.get("name"), "result": value})
    return results


def _retrieval_items(trace: dict) -> list[dict]:
    retrieval = trace.get("retrieval")
    if isinstance(retrieval, dict):
        items = retrieval.get("evidence", retrieval.get("hits", []))
        if isinstance(items, list):
            return items
    for item in _tool_results(trace):
        if item["name"] == "search_campus_knowledge":
            results = item["result"].get("results", [])
            return results if isinstance(results, list) else []
    return []


def _load_case_turns(implementation: str, case: dict, case_row: dict | None) -> list[dict]:
    turns = case.get("turns", [])
    if not case_row:
        return []
    manifest_value = case_row.get("manifest_path")
    if not manifest_value and case_row.get("run_id"):
        manifest_value = f"runs/{case_row['run_id']}/manifest.json"
    if not manifest_value:
        return []
    manifest_path = Path(manifest_value)
    if not manifest_path.is_absolute():
        manifest_path = ROOT / manifest_path
    if not manifest_path.is_file():
        return []
    run_dir = manifest_path.parent
    per_turn_path = run_dir / "per_turn.jsonl"
    if per_turn_path.is_file():
        per_turn_rows = _read_jsonl(per_turn_path)
        normalized = []
        for row in per_turn_rows:
            trace_path_value = row.get("trace_file")
            if not trace_path_value:
                continue
            trace_path = run_dir / trace_path_value
            if not trace_path.is_file():
                continue
            trace = _read_json(trace_path)
            normalized.append({"per_turn": row, "trace": trace, "run_dir": run_dir})
        return normalized

    if implementation == "principles" and len(turns) == 1:
        trace_name = _read_json(manifest_path).get("trace_file", "trace.json")
        trace_path = run_dir / trace_name
        if trace_path.is_file():
            trace = _read_json(trace_path)
            turn = turns[0]
            per_turn = {
                "run_id": case_row.get("run_id"),
                "case_id": case["case_id"],
                "turn_number": 1,
                "question": turn.get("content"),
                "expected_assistant_criteria": turn.get("expected_assistant_criteria"),
                "expected_answer_points": case.get("gold", {}).get("answer_points", []),
                "expected_caveats": case.get("gold", {}).get("required_caveats", []),
                "answer": trace.get("answer"),
                "status": trace.get("status"),
                "trace_file": str(trace_path.relative_to(run_dir)).replace("\\", "/"),
            }
            return [{"per_turn": per_turn, "trace": trace, "run_dir": run_dir}]
    return []


def _turn_duration_ms(implementation: str, trace: dict) -> float | None:
    if implementation == "engineering":
        value = trace.get("elapsed_seconds")
        return (
            round(float(value) * 1000, 3)
            if isinstance(value, (int, float)) and value >= 0
            else None
        )
    retrieval_ms = trace.get("retrieval", {}).get("latency_ms")
    requests = trace.get("model_requests", [])
    request_ms = [
        item.get("latency_ms")
        for item in requests
        if isinstance(item.get("latency_ms"), (int, float))
    ]
    if not isinstance(retrieval_ms, (int, float)):
        return None
    return round(retrieval_ms + sum(request_ms), 3)


def _task_completed(
    implementation: str,
    case: dict,
    per_turn: dict,
    trace: dict,
    expected_tool: dict | None,
) -> bool:
    answer = per_turn.get("answer") or trace.get("answer") or ""
    if not isinstance(answer, str) or not answer.strip():
        return False
    if per_turn.get("status") not in {"completed", "retrieval_only_complete"} and trace.get(
        "status"
    ) not in {"completed", "retrieval_only_complete"}:
        return False
    calls = _normalize_tool_calls(trace)
    if expected_tool is None:
        if calls:
            return False
        if implementation == "principles" and case.get("category") in {"knowledge", "unknown"}:
            return isinstance(trace.get("retrieval"), dict)
        return True
    if implementation == "principles" and case.get("category") in {"knowledge", "unknown"}:
        return isinstance(trace.get("retrieval"), dict)
    return task_tool_process_completed(expected_tool, calls, _tool_results(trace))


def derive(
    implementation: str, cases: list[dict], case_rows: dict[str, dict]
) -> tuple[list[dict], dict]:
    units: list[dict] = []
    categories = Counter()
    failed_missing_units = 0
    not_attempted_units = 0
    planned_turns = 0

    for case in cases:
        case_id = case["case_id"]
        expected_turns = case.get("turns", [])
        planned_turns += len(expected_turns)
        case_row = case_rows.get(case_id)
        loaded = _load_case_turns(implementation, case, case_row)
        seen_turn_numbers: set[int] = set()
        for item in loaded:
            per_turn, trace = item["per_turn"], item["trace"]
            turn_number = int(per_turn.get("turn_number", 1))
            if turn_number < 1 or turn_number > len(expected_turns):
                continue
            seen_turn_numbers.add(turn_number)
            gold_turn = expected_turns[turn_number - 1]
            expected_tool = _expected_tool(implementation, case, gold_turn)
            trusted_identity = case.get("context", {}).get("authenticated_user_id")
            actual_calls = _normalize_tool_calls(trace)
            is_tool_metric_applicable = implementation == "engineering" or case.get("category") in {
                "status",
                "multi_turn",
                "boundary",
            }
            contract = (
                tool_contract(expected_tool, actual_calls, trusted_identity=trusted_identity)
                if is_tool_metric_applicable
                else None
            )
            ranked_items = _retrieval_items(trace)
            retrieved_sources = unique_source_ids(ranked_items)
            expected_sources = case.get("gold", {}).get("source_ids", [])
            retrieval = retrieval_metrics(retrieved_sources, expected_sources)
            answer = per_turn.get("answer") or trace.get("answer") or ""
            tool_results = _tool_results(trace)
            unit = {
                "implementation": implementation,
                "case_id": case_id,
                "category": case["category"],
                "turn_number": turn_number,
                "attempted": True,
                "question": per_turn.get("question")
                or gold_turn.get("content")
                or gold_turn.get("user"),
                "answer": answer,
                "status": per_turn.get("status") or trace.get("status"),
                "expected_assistant_criteria": per_turn.get("expected_assistant_criteria")
                or gold_turn.get("expected_assistant_criteria"),
                "expected_answer_points": per_turn.get(
                    "expected_answer_points", case.get("gold", {}).get("answer_points", [])
                ),
                "expected_caveats": per_turn.get(
                    "expected_caveats", case.get("gold", {}).get("required_caveats", [])
                ),
                "expected_source_ids": expected_sources,
                "retrieved_source_ids": retrieved_sources,
                "retrieval": retrieval,
                "expected_tool": expected_tool,
                "actual_tool_calls": actual_calls,
                "tool_results": tool_results,
                "tool_contract": contract,
                "tool_metrics_applicable": is_tool_metric_applicable,
                "trusted_identity": trusted_identity,
                "task_completed": _task_completed(
                    implementation, case, per_turn, trace, expected_tool
                ),
                "execution_failed": (per_turn.get("status") or trace.get("status"))
                not in {"completed", "retrieval_only_complete"},
                "latency_ms": _turn_duration_ms(implementation, trace),
                "trace_file": per_turn.get("trace_file"),
                "judge_status": "pending",
                "judge_file": None,
                "unknown_handled": None,
            }
            evidence = ranked_items[:10]
            unit["judge_evidence"] = [
                {
                    key: value
                    for key, value in item.items()
                    if key
                    in {
                        "source_id",
                        "title",
                        "url",
                        "published_on",
                        "scope",
                        "text",
                        "rank",
                        "evidence_id",
                    }
                }
                for item in evidence
            ]
            units.append(unit)
            categories[case["category"]] += 1

        failed_attempt_added = False
        for turn_number, gold_turn in enumerate(expected_turns, start=1):
            if turn_number in seen_turn_numbers:
                continue
            failed_case = bool(case_row and case_row.get("status") == "failed")
            attempted = not failed_case or not failed_attempt_added
            if failed_case and attempted:
                failed_attempt_added = True
                failed_missing_units += 1
            if not attempted:
                not_attempted_units += 1
            expected_tool = _expected_tool(implementation, case, gold_turn)
            is_tool_metric_applicable = implementation == "engineering" or case.get("category") in {
                "status",
                "multi_turn",
                "boundary",
            }
            contract = (
                tool_contract(
                    expected_tool,
                    [],
                    trusted_identity=case.get("context", {}).get("authenticated_user_id"),
                )
                if is_tool_metric_applicable
                else None
            )
            no_trace_unit = {
                "implementation": implementation,
                "case_id": case_id,
                "category": case["category"],
                "turn_number": turn_number,
                "attempted": attempted,
                "question": gold_turn.get("content") or gold_turn.get("user"),
                "answer": "",
                "status": "runner_failed_before_trace"
                if attempted
                else "not_attempted_after_failure",
                "expected_assistant_criteria": gold_turn.get("expected_assistant_criteria"),
                "expected_answer_points": case.get("gold", {}).get("answer_points", []),
                "expected_caveats": case.get("gold", {}).get("required_caveats", []),
                "expected_source_ids": case.get("gold", {}).get("source_ids", []),
                "retrieved_source_ids": [],
                "retrieval": retrieval_metrics([], case.get("gold", {}).get("source_ids", [])),
                "expected_tool": expected_tool,
                "actual_tool_calls": [],
                "tool_results": [],
                "tool_contract": contract,
                "tool_metrics_applicable": is_tool_metric_applicable,
                "trusted_identity": case.get("context", {}).get("authenticated_user_id"),
                "task_completed": False,
                "execution_failed": attempted,
                "latency_ms": None,
                "trace_file": None,
                "judge_status": "missing_response" if attempted else "not_attempted",
                "judge_file": None,
                "unknown_handled": False
                if attempted and case.get("category") == "unknown"
                else None,
                "judge_evidence": [],
            }
            units.append(no_trace_unit)
            categories[case["category"]] += 1

    retrieval_rows = [
        unit for unit in units if unit["attempted"] and unit["retrieval"]["applicable"]
    ]
    retrieval_agg = {}
    for metric in ("recall_at_1", "recall_at_3", "recall_at_5", "mrr_at_5"):
        values = [unit["retrieval"][metric] for unit in retrieval_rows]
        retrieval_agg[metric] = {
            "sum": sum(values),
            "denominator": len(values),
            "mean": average(values),
        }

    tool_units = [unit for unit in units if unit["tool_metrics_applicable"] and unit["attempted"]]
    selected = [
        unit
        for unit in tool_units
        if unit["tool_contract"] and unit["tool_contract"]["tool_selection_match"]
    ]
    argument_units = [
        unit
        for unit in tool_units
        if unit["expected_tool"] and unit["expected_tool"]["name"] != "search_campus_knowledge"
    ]
    argument_correct = [
        unit
        for unit in argument_units
        if unit["tool_contract"] and unit["tool_contract"]["argument_match"]
    ]
    identity_units = [
        unit
        for unit in argument_units
        if unit["tool_contract"] and unit["tool_contract"]["trusted_identity_match"] is not None
    ]
    identity_correct = [
        unit for unit in identity_units if unit["tool_contract"]["trusted_identity_match"]
    ]
    completion_units = [unit for unit in units if unit["attempted"]]

    latencies = [unit["latency_ms"] for unit in units if unit["latency_ms"] is not None]
    attempted_count = len(completion_units)
    failed_count = sum(unit["execution_failed"] for unit in completion_units)
    test_summary_path = ROOT / "runs" / "windows-test-summary-baseline.json"
    current_test_summary_path = ROOT / "runs" / "windows-test-summary.json"
    test_summary = _read_json(test_summary_path) if test_summary_path.is_file() else None
    current_test_summary = (
        _read_json(current_test_summary_path) if current_test_summary_path.is_file() else None
    )
    test_rate = None
    if test_summary:
        test_denominator = test_summary.get("passed", 0) + test_summary.get("failed", 0)
        test_rate = test_summary.get("passed", 0) / test_denominator if test_denominator else None
    metrics = {
        "implementation": implementation,
        "planned_turn_count": planned_turns,
        "observed_turn_count": len(units),
        "untraced_failed_turn_count": failed_missing_units,
        "not_attempted_turn_count": not_attempted_units,
        "category_turn_unit_counts": dict(sorted(categories.items())),
        "retrieval": {
            "applicable_turn_count": len(retrieval_rows),
            "not_applicable_turn_count": len(units) - len(retrieval_rows),
            "metrics": retrieval_agg,
        },
        "agent": {
            "tool_selection_accuracy": {
                "numerator": len(selected),
                "denominator": len(tool_units),
                "rate": len(selected) / len(tool_units) if tool_units else None,
            },
            "tool_argument_accuracy": {
                "numerator": len(argument_correct),
                "denominator": len(argument_units),
                "rate": len(argument_correct) / len(argument_units) if argument_units else None,
                "trusted_identity_match": {
                    "numerator": len(identity_correct),
                    "denominator": len(identity_units),
                    "rate": len(identity_correct) / len(identity_units) if identity_units else None,
                },
            },
            "task_completion_rate": {
                "numerator": sum(unit["task_completed"] for unit in completion_units),
                "denominator": len(completion_units),
                "rate": sum(unit["task_completed"] for unit in completion_units)
                / len(completion_units)
                if completion_units
                else None,
            },
            "unknown_handling_rate": {
                "numerator": sum(
                    unit["unknown_handled"] is True
                    for unit in units
                    if unit["category"] == "unknown"
                ),
                "denominator": sum(
                    unit["unknown_handled"] is not None
                    for unit in units
                    if unit["category"] == "unknown"
                ),
                "pending_judgements": sum(
                    unit["category"] == "unknown" and unit["unknown_handled"] is None
                    for unit in units
                ),
            },
        },
        "engineering": {
            "latency_scope": "See evaluation/metric_spec_v1.json; measurements are implementation-specific by design.",
            "average_latency_ms": average(latencies),
            "p95_latency_ms_nearest_rank": nearest_rank_percentile(latencies, 0.95),
            "latency_sample_count": len(latencies),
            "latency_unavailable_count": len(units) - len(latencies),
            "latency_samples_ms": latencies,
            "error_rate": {
                "numerator": failed_count,
                "denominator": attempted_count,
                "rate": failed_count / attempted_count if attempted_count else None,
            },
            "test_pass_rate": {
                "rate": test_rate,
                "source": str(test_summary_path.relative_to(ROOT)).replace("\\", "/")
                if test_summary
                else None,
                "skipped_reported_separately": test_summary.get("skipped")
                if test_summary
                else None,
            },
            "current_windows_test_pass_rate": {
                "rate": current_test_summary.get("test_pass_rate")
                if current_test_summary
                else None,
                "source": str(current_test_summary_path.relative_to(ROOT)).replace("\\", "/")
                if current_test_summary
                else None,
                "skipped_reported_separately": current_test_summary.get("skipped")
                if current_test_summary
                else None,
            },
        },
    }
    return units, metrics


def apply_judgements(units: list[dict], judgement_rows: list[dict]) -> dict:
    latest = {}
    for row in judgement_rows:
        latest[row["item_id"]] = row
    for unit in units:
        item_id = f"{unit['implementation']}::{unit['case_id']}::{unit['turn_number']}"
        judgement = latest.get(item_id)
        if judgement and judgement.get("status") == "completed":
            unit["judge_status"] = "completed"
            unit["judge_file"] = judgement.get("raw_file")
            unit["judge_scores"] = judgement.get("scores")
            unit["unknown_handled"] = judgement.get("scores", {}).get("unknown_handled")
        elif unit.get("answer") and unit.get("attempted"):
            unit["judge_status"] = judgement.get("status", "pending") if judgement else "pending"
            unit["judge_error_type"] = judgement.get("error_type") if judgement else None

    answer_metrics = {}
    for dimension in ("correctness", "faithfulness", "citation_accuracy"):
        applicable = [
            unit
            for unit in units
            if unit["attempted"]
            and (dimension != "citation_accuracy" or bool(unit["expected_source_ids"]))
        ]
        scored = []
        pending_count = 0
        missing_count = 0
        for unit in applicable:
            if not unit.get("answer"):
                scored.append(0)
                missing_count += 1
            elif unit.get("judge_scores") is not None:
                scored.append(unit["judge_scores"].get(dimension))
                if scored[-1] is None:
                    pending_count += 1
                    scored.pop()
            else:
                pending_count += 1
        score_sum = sum(scored)
        denominator = len(applicable)
        normalized_numerator = score_sum / 2
        complete = pending_count == 0
        answer_metrics[dimension] = {
            "raw_score_sum": score_sum,
            "normalized_numerator": normalized_numerator,
            "denominator_attempted_turns": denominator,
            "mean_over_scored_or_missing": normalized_numerator / denominator
            if denominator
            else None,
            "complete_mean": normalized_numerator / denominator
            if denominator and complete
            else None,
            "scored_turn_count_including_zero_missing": len(scored),
            "missing_response_count_scored_zero": missing_count,
            "pending_judgement_count": pending_count,
            "not_applicable_turn_count": len([unit for unit in units if unit["attempted"]])
            - denominator,
            "status": "complete" if complete else "partial",
        }
    unknown_units = [unit for unit in units if unit["attempted"] and unit["category"] == "unknown"]
    unknown_pending = sum(
        bool(unit.get("answer")) and unit.get("judge_scores") is None for unit in unknown_units
    )
    unknown_handled = sum(unit.get("unknown_handled") is True for unit in unknown_units)
    answer_metrics["unknown_handling_rate"] = {
        "numerator": unknown_handled,
        "denominator_attempted_unknown_turns": len(unknown_units),
        "rate_over_attempted_unknown_turns": unknown_handled / len(unknown_units)
        if unknown_units
        else None,
        "pending_judgement_count": unknown_pending,
        "status": "complete" if unknown_pending == 0 else "partial",
    }
    answer_metrics["judge_model"] = "deepseek-flash"
    answer_metrics["judge_limitations"] = (
        "Same model family is used for generation and judging; scores are a model-assisted proxy, not independent human validation. H-03 manual V1/V2 ratings remain separate."
    )
    answer_metrics["judge_attempt_count"] = len(judgement_rows)
    answer_metrics["judge_success_count"] = sum(
        row.get("status") == "completed" for row in judgement_rows
    )
    answer_metrics["judge_failure_count"] = sum(
        row.get("status") != "completed" for row in judgement_rows
    )
    return answer_metrics


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--principles-run-id", default=RUN_IDS["principles"])
    parser.add_argument("--engineering-run-id", default=RUN_IDS["engineering"])
    parser.add_argument(
        "--implementations", nargs="+", choices=IMPLEMENTATIONS, default=list(IMPLEMENTATIONS)
    )
    args = parser.parse_args()
    if sys.platform != "win32":
        raise SystemExit("Run frozen metric aggregation with the Windows project .venv.")
    dataset = _read_json(ROOT / "evaluation" / "frozen_cases.json")
    cases = dataset["cases"]
    evaluation_dir = ROOT / "runs" / args.run_id
    evaluation_dir.mkdir(parents=True, exist_ok=True)
    all_metrics = {
        "evaluation_run_id": args.run_id,
        "created_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds"),
        "dataset_id": dataset["dataset_id"],
        "metric_spec_id": "campus-customer-service-metrics-v1.1",
        "answer_judge_pending": True,
        "implementations": {},
    }
    judge_rows = []
    judgement_path = evaluation_dir / "judgements.jsonl"
    existing_judgements = _read_jsonl(judgement_path)
    input_run_ids = {
        "principles": args.principles_run_id,
        "engineering": args.engineering_run_id,
    }
    for implementation in args.implementations:
        parent_dir = ROOT / "runs" / input_run_ids[implementation]
        parent_path = parent_dir / "manifest.json"
        rows_path = parent_dir / "per_case.jsonl"
        if not parent_path.is_file():
            raise SystemExit(f"Missing baseline manifest: {parent_path}")
        parent = _read_json(parent_path)
        if parent.get("status") not in {"complete", "incomplete", "in_progress"}:
            raise SystemExit(f"Unexpected baseline state for {implementation}.")
        latest = {}
        for row in _read_jsonl(rows_path):
            latest[row["case_id"]] = row
        expected_case_ids = {case["case_id"] for case in cases}
        if expected_case_ids - set(latest):
            missing = sorted(expected_case_ids - set(latest))
            raise SystemExit(
                f"Baseline {implementation} is not fully attempted yet; missing case records: {missing}"
            )
        units, metrics = derive(implementation, cases, latest)
        metrics["answer"] = apply_judgements(
            units,
            [row for row in existing_judgements if row.get("implementation") == implementation],
        )
        metrics["agent"]["unknown_handling_rate"] = metrics["answer"]["unknown_handling_rate"]
        all_metrics["implementations"][implementation] = metrics
        for unit in units:
            if unit.get("answer"):
                judge_rows.append(unit)
        units_path = evaluation_dir / f"{implementation}_units.jsonl"
        units_path.write_text(
            "".join(json.dumps(unit, ensure_ascii=False, sort_keys=True) + "\n" for unit in units),
            encoding="utf-8",
        )
        print(
            f"derived {implementation}: turns={len(units)} retrieval={metrics['retrieval']['applicable_turn_count']} errors={metrics['engineering']['error_rate']['numerator']}/{metrics['engineering']['error_rate']['denominator']}",
            flush=True,
        )

    judge_input_path = evaluation_dir / "judge_input.jsonl"
    judge_input_path.write_text(
        "".join(json.dumps(unit, ensure_ascii=False, sort_keys=True) + "\n" for unit in judge_rows),
        encoding="utf-8",
    )
    all_metrics["judge_input_file"] = str(judge_input_path.relative_to(ROOT)).replace("\\", "/")
    all_metrics["judge_input_count"] = len(judge_rows)
    all_metrics["answer_metrics"] = {
        "status": "complete"
        if all(
            not any(
                value.get("pending_judgement_count", 0)
                for value in metrics["answer"].values()
                if isinstance(value, dict)
            )
            for metrics in all_metrics["implementations"].values()
        )
        else "pending_or_partial",
        "per_implementation": {
            name: metrics["answer"] for name, metrics in all_metrics["implementations"].items()
        },
        "judgement_file": str(judgement_path.relative_to(ROOT)).replace("\\", "/")
        if judgement_path.exists()
        else None,
    }
    all_metrics["answer_judge_pending"] = all_metrics["answer_metrics"]["status"] != "complete"
    (evaluation_dir / "metric_results.json").write_text(
        json.dumps(all_metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "evaluation_run_id": args.run_id,
                "judge_input_count": len(judge_rows),
                "status": "derived",
            },
            ensure_ascii=False,
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
