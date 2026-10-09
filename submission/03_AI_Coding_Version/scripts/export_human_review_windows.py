"""Create a blank-score Excel-friendly sheet from the saved V1/V2 answer traces."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
COMPARISONS = {
    "V1": "rag-prompt-ab-v1-20261006-175830",
    "V2": "rag-prompt-ab-v2-20261006-175916",
}
CASE_IDS = ("K01", "K05", "K06", "K09", "K10")
OUTPUT = PROJECT_ROOT / "reports" / "人工评分表_V1_V2.csv"
FIELDNAMES = (
    "case_id",
    "prompt_version",
    "question",
    "answer",
    "standard_answer_points",
    "required_caveats",
    "retrieved_sources",
    "trace_path",
    "correctness_0_2",
    "correctness_reason",
    "faithfulness_0_2",
    "faithfulness_reason",
    "citation_accuracy_0_2",
    "citation_accuracy_reason",
    "reviewer",
    "review_date",
)


def main() -> int:
    if sys.platform != "win32":
        raise SystemExit("Run this material export with the Windows project .venv.")
    if OUTPUT.exists():
        raise SystemExit(f"Refusing to overwrite an existing review sheet: {OUTPUT.name}")
    frozen = json.loads(
        (PROJECT_ROOT / "evaluation" / "frozen_cases.json").read_text(encoding="utf-8")
    )
    cases = {case["case_id"]: case for case in frozen["cases"]}
    rows = []
    for version, run_id in COMPARISONS.items():
        for case_id in CASE_IDS:
            trace_path = PROJECT_ROOT / "runs" / run_id / "traces" / f"{case_id}.json"
            trace = json.loads(trace_path.read_text(encoding="utf-8"))
            if trace.get("status") != "completed" or trace.get("answer") is None:
                raise ValueError(f"No completed answer for {version}/{case_id}.")
            case = cases[case_id]
            source_map = {}
            for payload in trace.get("tool_results", []):
                for result in payload.get("results", []):
                    source_map[result.get("source_id")] = {
                        "title": result.get("title"),
                        "url": result.get("url"),
                        "published_on": result.get("published_on"),
                        "scope": result.get("scope"),
                        "index_policy": result.get("index_policy"),
                    }
            rows.append(
                {
                    "case_id": case_id,
                    "prompt_version": version,
                    "question": case["turns"][0]["content"],
                    "answer": trace["answer"],
                    "standard_answer_points": "\n".join(
                        case.get("gold", {}).get("answer_points", [])
                    ),
                    "required_caveats": "\n".join(case.get("gold", {}).get("required_caveats", [])),
                    "retrieved_sources": json.dumps(source_map, ensure_ascii=False, sort_keys=True),
                    "trace_path": trace_path.relative_to(PROJECT_ROOT).as_posix(),
                    "correctness_0_2": "",
                    "correctness_reason": "",
                    "faithfulness_0_2": "",
                    "faithfulness_reason": "",
                    "citation_accuracy_0_2": "",
                    "citation_accuracy_reason": "",
                    "reviewer": "",
                    "review_date": "",
                }
            )

    with OUTPUT.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({"output": OUTPUT.name, "rows": len(rows), "scores_filled": 0}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
