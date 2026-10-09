"""Run up to two pending five-item judge batches and save progress after each batch."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from run_answer_judges_windows import run_batch  # noqa: E402


def _jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evaluation-run-id", required=True)
    parser.add_argument("--implementation", choices=("principles", "engineering"), required=True)
    parser.add_argument("--max-batches", type=int, choices=(1, 2), default=2)
    parser.add_argument("--timeout-seconds", type=float, default=45)
    args = parser.parse_args()
    if sys.platform != "win32":
        raise SystemExit("Run judge batches with the Windows project .venv.")
    if args.timeout_seconds <= 0:
        parser.error("--timeout-seconds must be positive")

    eval_dir = ROOT / "runs" / args.evaluation_run_id
    dataset = _jsonl(eval_dir / "judge_input.jsonl")
    judged = _jsonl(eval_dir / "judgements.jsonl")
    completed = {row["item_id"] for row in judged if row.get("status") == "completed"}
    selected = [
        f"{row['implementation']}::{row['case_id']}::{row['turn_number']}"
        for row in dataset
        if row.get("implementation") == args.implementation
        and f"{row['implementation']}::{row['case_id']}::{row['turn_number']}" not in completed
    ]
    batches = [selected[index : index + 5] for index in range(0, len(selected), 5)]
    if not batches:
        print(f"{args.implementation}: all judge items already complete", flush=True)
        return 0
    chosen_batches = batches[: args.max_batches]
    failures = 0
    for number, item_ids in enumerate(chosen_batches, start=1):
        print(
            f"starting {args.implementation} judge batch {number}/{len(chosen_batches)}; items={len(item_ids)}; remaining_after_batch={len(selected) - number * 5 if number < len(chosen_batches) else max(0, len(selected) - sum(len(group) for group in chosen_batches[:number]))}",
            flush=True,
        )
        status = run_batch(args.evaluation_run_id, item_ids, args.timeout_seconds)
        failures += status != 0
        print(f"finished {args.implementation} judge batch {number}; status={'failed' if status else 'complete'}", flush=True)
    print(
        json.dumps(
            {
                "implementation": args.implementation,
                "batches_run": len(chosen_batches),
                "items_run": sum(len(group) for group in chosen_batches),
                "pending_after_run": max(0, len(selected) - sum(len(group) for group in chosen_batches)),
                "batch_failures": failures,
            },
            ensure_ascii=False,
        ),
        flush=True,
    )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
