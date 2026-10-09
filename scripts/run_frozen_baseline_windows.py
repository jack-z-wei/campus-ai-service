"""Run/resume bounded batches of the frozen case set using the Windows project .venv."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _append_jsonl(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n")


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _manifest_reference(run_id: str | None, value: str | None = None) -> str | None:
    if value:
        candidate = Path(value)
        if not candidate.is_absolute():
            candidate = ROOT / candidate
        try:
            if candidate.is_file():
                return str(candidate.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
        except (ValueError, OSError):
            pass
    if run_id:
        candidate = ROOT / "runs" / run_id / "manifest.json"
        try:
            if candidate.is_file():
                return str(candidate.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
        except (ValueError, OSError):
            return None
    return None


def _last_child_json(output: str) -> dict | None:
    decoder = json.JSONDecoder()
    for start, character in enumerate(output):
        if character != "{":
            continue
        try:
            value, _ = decoder.raw_decode(output[start:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and "run_id" in value and "status" in value:
            return value
    return None


def _case_map() -> dict[str, dict]:
    dataset = json.loads((ROOT / "evaluation" / "frozen_cases.json").read_text(encoding="utf-8"))
    return {case["case_id"]: case for case in dataset["cases"]}


def _current_multiturn_fingerprint(implementation: str) -> dict[str, str]:
    if implementation == "principles":
        paths = [
            ROOT / "src" / "campus" / "principle_agent.py",
            ROOT / "src" / "campus" / "principle_tools.py",
            ROOT / "src" / "campus" / "conversation_memory.py",
            ROOT / "src" / "campus" / "runtime.py",
        ]
        return {
            f"{path.parent.name}/{path.name}": hashlib.sha256(path.read_bytes()).hexdigest()
            for path in paths
        }
    paths = [
        ROOT / "src" / "agents" / "campus_customer_service.py",
        ROOT / "src" / "agents" / "campus_tools.py",
        ROOT / "src" / "campus" / "knowledge.py",
        ROOT / "src" / "campus" / "retrieval.py",
        ROOT / "src" / "campus" / "retrieval_chroma.py",
        ROOT / "src" / "campus" / "runtime.py",
        ROOT / "src" / "campus" / "tools" / "status.py",
    ]
    return {
        path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in paths
    }


def _find_reusable_multiturn(implementation: str, case_id: str) -> dict | None:
    prefix = "principles-multiturn-" if implementation == "principles" else "engineering-multiturn-"
    prompt_path = ROOT / "prompts" / "campus_system_v1.md"
    source_manifest_path = ROOT / "docs" / "campus" / "source_manifest.json"
    frozen_cases_path = ROOT / "evaluation" / "frozen_cases.json"
    expected_inputs = {
        "prompt_sha256": hashlib.sha256(prompt_path.read_bytes()).hexdigest(),
        "source_manifest_sha256": hashlib.sha256(source_manifest_path.read_bytes()).hexdigest(),
        "frozen_cases_sha256": hashlib.sha256(frozen_cases_path.read_bytes()).hexdigest(),
    }
    candidates = []
    for manifest_path in (ROOT / "runs").glob(f"{prefix}*/manifest.json"):
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if manifest.get("case_id") != case_id or manifest.get("status") != "completed":
            continue
        if implementation == "principles" and manifest.get("prompt_version") != "v1":
            continue
        if manifest.get("implementation_sha256") != _current_multiturn_fingerprint(implementation):
            continue
        if any(manifest.get(key) != value for key, value in expected_inputs.items()):
            continue
        run_dir = manifest_path.parent
        per_turn_path = run_dir / "per_turn.jsonl"
        rows = _read_jsonl(per_turn_path)
        case = _case_map()[case_id]
        if len(rows) != len(case["turns"]):
            continue
        if any(
            not row.get("trace_file") or not (run_dir / row["trace_file"]).is_file() for row in rows
        ):
            continue
        finished = manifest.get("finished_at", "")
        candidates.append((finished, manifest, manifest_path, per_turn_path))
    if not candidates:
        return None
    _, manifest, manifest_path, per_turn_path = sorted(candidates, key=lambda item: item[0])[-1]
    return {
        "run_id": manifest["run_id"],
        "manifest_path": str(manifest_path.relative_to(ROOT)).replace("\\", "/"),
        "per_turn_path": str(per_turn_path.relative_to(ROOT)).replace("\\", "/"),
        "reused_existing_evidence": True,
    }


def _child_command(implementation: str, case_id: str, timeout_seconds: float) -> list[str]:
    if implementation == "principles":
        script = (
            "run_campus_principles_multiturn_windows.py"
            if case_id.startswith("M")
            else "run_campus_principles_windows.py"
        )
        command = [sys.executable, str(ROOT / "scripts" / script), "--case-id", case_id]
        if script == "run_campus_principles_windows.py":
            command.extend(("--prompt-version", "v1", "--top-k", "5"))
        else:
            command.extend(("--prompt-version", "v1", "--top-k", "5"))
        return command
    script = ROOT / "scripts" / "run_campus_agent_multiturn_windows.py"
    return [
        sys.executable,
        str(script),
        "--case-id",
        case_id,
        "--timeout-seconds",
        str(timeout_seconds),
    ]


def run_batch(implementation: str, run_id: str, case_ids: list[str], timeout_seconds: float) -> int:
    if sys.platform != "win32":
        raise SystemExit("Run this baseline runner with the Windows project .venv.")
    if not 1 <= len(case_ids) <= 5:
        raise SystemExit("Submit 1 to 5 frozen cases per batch.")
    if len(case_ids) != len(set(case_ids)):
        raise SystemExit("Duplicate case IDs are not allowed in one batch.")

    cases = _case_map()
    unknown = [case_id for case_id in case_ids if case_id not in cases]
    if unknown:
        raise SystemExit(f"Unknown frozen case IDs: {unknown}")
    run_dir = ROOT / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = run_dir / "manifest.json"
    per_case_path = run_dir / "per_case.jsonl"
    progress_path = run_dir / "progress.jsonl"
    existing_rows = _read_jsonl(per_case_path)
    repaired_rows = False
    for row in existing_rows:
        if row.get("status") == "completed" and not row.get("reused_existing_evidence"):
            normalized = _manifest_reference(row.get("run_id"), row.get("manifest_path"))
            if normalized and normalized != row.get("manifest_path"):
                row["manifest_path"] = normalized
                repaired_rows = True
    if repaired_rows:
        per_case_path.write_text(
            "".join(
                json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in existing_rows
            ),
            encoding="utf-8",
        )
    completed = {
        row["case_id"]
        for row in existing_rows
        if row.get("status") == "completed" and row.get("implementation") == implementation
    }
    started = datetime.now(ZoneInfo("Asia/Shanghai"))
    manifest = (
        json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest_path.exists()
        else {
            "run_id": run_id,
            "implementation": implementation,
            "started_at": started.isoformat(timespec="seconds"),
            "dataset_id": "campus-customer-service-frozen-v1",
            "planned_case_ids": [],
            "requested_case_ids": [],
            "status": "in_progress",
            "batch_limit": 5,
            "max_child_timeout_seconds": timeout_seconds,
            "per_case_file": "per_case.jsonl",
            "progress_file": "progress.jsonl",
        }
    )
    if manifest.get("implementation") != implementation:
        raise SystemExit("The run_id is already bound to a different implementation.")
    manifest["planned_case_ids"] = list(dict.fromkeys(manifest["planned_case_ids"] + case_ids))
    manifest["requested_case_ids"] = case_ids
    manifest["status"] = "in_progress"
    _write_json(manifest_path, manifest)

    for case_id in case_ids:
        if case_id in completed:
            print(f"skip {case_id}: completed evidence already recorded", flush=True)
            continue
        case = cases[case_id]
        row = {
            "implementation": implementation,
            "case_id": case_id,
            "category": case["category"],
            "status": "running",
            "started_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds"),
        }
        if case.get("category") == "multi_turn":
            reused = _find_reusable_multiturn(implementation, case_id)
            if reused:
                row.update(reused)
                row["status"] = "completed"
                row["duration_seconds"] = None
                row["timing_source"] = "per-turn trace; original task run reused"
                row["finished_at"] = datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(
                    timespec="seconds"
                )
                _append_jsonl(per_case_path, row)
                _append_jsonl(
                    progress_path,
                    {
                        "case_id": case_id,
                        "status": "reused_existing_evidence",
                        "run_id": reused["run_id"],
                    },
                )
                completed.add(case_id)
                print(f"reused {case_id}: {reused['run_id']}", flush=True)
                continue

        argv = _child_command(implementation, case_id, timeout_seconds)
        attempt_started = time.monotonic()
        try:
            result = subprocess.run(
                argv,
                cwd=ROOT,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=max(timeout_seconds + 60, 90),
                check=False,
            )
            child = _last_child_json(result.stdout)
            row.update(
                {
                    "status": "completed"
                    if result.returncode == 0 and child and child.get("status") == "completed"
                    else "failed",
                    "child_exit_code": result.returncode,
                    "run_id": child.get("run_id") if child else None,
                    "manifest_path": child.get("manifest") if child else None,
                    "reused_existing_evidence": False,
                }
            )
            if row.get("manifest_path"):
                row["manifest_path"] = _manifest_reference(row.get("run_id"), row["manifest_path"])
            if not row.get("manifest_path"):
                row["manifest_path"] = _manifest_reference(row.get("run_id"))
            if row["status"] == "failed":
                row["error_type"] = (child or {}).get("error_type") or "ChildProcessFailed"
            # Child stdout may contain model answers; keep it in memory only and never write it here.
        except subprocess.TimeoutExpired:
            row.update({"status": "failed", "error_type": "ChildProcessTimeout"})
        row["duration_seconds"] = round(time.monotonic() - attempt_started, 3)
        row["finished_at"] = datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds")
        _append_jsonl(per_case_path, row)
        _append_jsonl(
            progress_path,
            {
                key: row.get(key)
                for key in ("case_id", "status", "run_id", "duration_seconds", "error_type")
            },
        )
        _write_json(manifest_path, manifest)
        print(
            f"{row['status']} {case_id} run={row.get('run_id') or 'unavailable'} elapsed={row['duration_seconds']}s",
            flush=True,
        )
        if row["status"] == "completed":
            completed.add(case_id)

    all_rows = _read_jsonl(per_case_path)
    latest = {}
    for item in all_rows:
        if item.get("implementation") == implementation:
            latest[item["case_id"]] = item
    manifest.update(
        {
            "finished_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds"),
            "completed_case_count": sum(
                item.get("status") == "completed" for item in latest.values()
            ),
            "failed_case_count": sum(item.get("status") == "failed" for item in latest.values()),
            "status": "complete"
            if all(
                latest.get(case_id, {}).get("status") == "completed"
                for case_id in manifest["planned_case_ids"]
            )
            else "incomplete",
        }
    )
    _write_json(manifest_path, manifest)
    print(
        json.dumps(
            {
                key: manifest[key]
                for key in (
                    "run_id",
                    "implementation",
                    "requested_case_ids",
                    "completed_case_count",
                    "failed_case_count",
                    "status",
                )
            },
            ensure_ascii=False,
        ),
        flush=True,
    )
    return (
        0
        if all(latest.get(case_id, {}).get("status") == "completed" for case_id in case_ids)
        else 1
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--implementation", choices=("principles", "engineering"), required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--case-ids", nargs="+", required=True)
    parser.add_argument("--timeout-seconds", type=float, default=120)
    args = parser.parse_args()
    if args.timeout_seconds <= 0:
        parser.error("--timeout-seconds must be positive")
    return run_batch(args.implementation, args.run_id, args.case_ids, args.timeout_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
