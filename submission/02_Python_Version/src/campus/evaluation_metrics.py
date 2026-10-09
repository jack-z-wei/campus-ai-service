"""Pure, versioned metric helpers for the frozen campus evaluation set."""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from typing import Any


def unique_source_ids(ranked_items: Iterable[Mapping[str, Any]]) -> list[str]:
    """Return source IDs in first-hit rank order, deduplicated by source."""
    ordered: list[str] = []
    seen: set[str] = set()
    for item in ranked_items:
        source_id = item.get("source_id")
        if isinstance(source_id, str) and source_id and source_id not in seen:
            seen.add(source_id)
            ordered.append(source_id)
    return ordered


def retrieval_metrics(ranked_source_ids: Iterable[str], relevant_source_ids: Iterable[str]) -> dict[str, Any]:
    ranked = list(dict.fromkeys(source_id for source_id in ranked_source_ids if source_id))
    relevant = set(source_id for source_id in relevant_source_ids if source_id)
    if not relevant:
        return {
            "applicable": False,
            "relevant_source_count": 0,
            "retrieved_unique_source_ids": ranked,
            "recall_at_1": None,
            "recall_at_3": None,
            "recall_at_5": None,
            "mrr_at_5": None,
        }
    first_rank = next(
        (rank for rank, source_id in enumerate(ranked[:5], start=1) if source_id in relevant),
        None,
    )
    found_at = {
        k: len(set(ranked[:k]) & relevant) for k in (1, 3, 5)
    }
    return {
        "applicable": True,
        "relevant_source_count": len(relevant),
        "retrieved_unique_source_ids": ranked,
        **{f"recall_at_{k}": found_at[k] / len(relevant) for k in (1, 3, 5)},
        "mrr_at_5": 1 / first_rank if first_rank is not None else 0.0,
    }


def tool_contract(
    expected: Mapping[str, Any] | None,
    actual_calls: Iterable[Mapping[str, Any]],
    *,
    trusted_identity: str | None = None,
) -> dict[str, Any]:
    """Check allowed tool selection and frozen argument subset for one turn."""
    calls = [
        {
            "name": item.get("name"),
            "arguments": item.get("arguments", {})
            if isinstance(item.get("arguments", {}), Mapping)
            else {},
        }
        for item in actual_calls
    ]
    if expected is None:
        return {
            "applicable": True,
            "expected_tool_name_sequence": [],
            "actual_tool_name_sequence": [item["name"] for item in calls],
            "tool_selection_match": not calls,
            "argument_match": None,
            "trusted_identity_match": None,
        }
    expected_name = expected.get("name")
    if expected_name == "create_human_service_request":
        name_matches = len(calls) == 1 and calls[0]["name"] == expected_name
    else:
        name_matches = bool(calls) and all(item["name"] == expected_name for item in calls)
    expected_arguments = expected.get("arguments", {})
    identity_expected = expected_arguments.get("requester_user_id")
    identity_match = (
        trusted_identity == identity_expected if identity_expected is not None else None
    )
    scored_arguments = {
        key: value for key, value in expected_arguments.items() if key != "requester_user_id"
    }
    arguments_match = bool(name_matches) and all(
        all(item["arguments"].get(key) == value for key, value in scored_arguments.items())
        for item in calls
    )
    return {
        "applicable": True,
        "expected_tool_name_sequence": [expected_name],
        "actual_tool_name_sequence": [item["name"] for item in calls],
        "tool_selection_match": name_matches,
        "argument_match": arguments_match,
        "trusted_identity_match": identity_match,
    }


def task_tool_process_completed(
    expected: Mapping[str, Any] | None,
    actual_calls: Iterable[Mapping[str, Any]],
    tool_results: Iterable[Mapping[str, Any]],
) -> bool:
    """Check expected action/result independently of strict tool accuracy."""
    calls = list(actual_calls)
    results = list(tool_results)
    if expected is None:
        return not calls
    name = expected.get("name")
    if not any(item.get("name") == name for item in calls):
        return False
    expected_result = expected.get("result")
    outcomes = [
        item.get("result", {}).get("outcome")
        for item in results
        if item.get("name") == name and isinstance(item.get("result"), Mapping)
    ]
    if expected_result == "ok_or_no_evidence":
        return any(outcome in {"ok", "no_evidence"} for outcome in outcomes)
    return expected_result is None or expected_result in outcomes


def average(values: Iterable[float]) -> float | None:
    sample = list(values)
    return sum(sample) / len(sample) if sample else None


def nearest_rank_percentile(values: Iterable[float], percentile: float) -> float | None:
    sample = sorted(values)
    if not sample:
        return None
    if not 0 < percentile <= 1:
        raise ValueError("percentile must be in (0, 1].")
    rank = math.ceil(percentile * len(sample))
    return sample[rank - 1]


def ordinal_mean(scores: Iterable[int]) -> dict[str, float | int | None]:
    sample = list(scores)
    if any(score not in (0, 1, 2) for score in sample):
        raise ValueError("Ordinal judge scores must be 0, 1, or 2.")
    return {
        "score_sum": sum(sample),
        "normalized_numerator": sum(sample) / 2,
        "denominator": len(sample),
        "normalized_mean": average(score / 2 for score in sample),
    }
