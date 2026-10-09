"""Validate the frozen course cases against the captured sources and demo seed."""

from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FROZEN = ROOT / "evaluation" / "frozen_cases.json"
SOURCE_MANIFEST = ROOT / "docs" / "campus" / "source_manifest.json"
SIMULATION_DATA = ROOT / "data" / "campus" / "simulation_records.json"


def main() -> int:
    if sys.platform != "win32":
        raise SystemExit("Run this evaluation integrity check with the Windows project venv.")
    frozen = json.loads(FROZEN.read_text(encoding="utf-8"))
    source_manifest = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
    simulation = json.loads(SIMULATION_DATA.read_text(encoding="utf-8"))
    cases = frozen.get("cases", [])
    category_counts = Counter(case.get("category") for case in cases)
    issues: list[str] = []
    source_ids = {source["id"] for source in source_manifest.get("sources", [])}
    case_ids = [case.get("case_id") for case in cases]
    if len(cases) != 21:
        issues.append(f"expected 21 cases; found {len(cases)}")
    if len(case_ids) != len(set(case_ids)):
        issues.append("case_id values are not unique")
    declared = {key: value for key, value in frozen.get("counts", {}).items() if key != "total"}
    if dict(category_counts) != declared:
        issues.append(f"category counts differ: {dict(category_counts)}")
    if frozen.get("counts", {}).get("total") != len(cases):
        issues.append("declared total does not match the number of cases")

    for case in cases:
        for source_id in case.get("gold", {}).get("source_ids", []):
            if source_id not in source_ids:
                issues.append(f"{case.get('case_id')} references unknown source {source_id}")

    if not simulation.get("all_records_simulated") or not simulation.get("not_real_student_records"):
        issues.append("simulation seed is not explicitly marked synthetic")
    seed_ids = {record["record_id"] for record in simulation.get("records", [])}
    for record in simulation.get("records", []):
        if not record["record_id"].startswith("SIM-") or not record["owner_user_id"].startswith("SIM-"):
            issues.append(f"non-synthetic identifier in seed: {record.get('record_id')}")

    def check_tool(case_id: str, tool: dict | None) -> None:
        if not tool:
            return
        record_id = tool.get("arguments", {}).get("record_id")
        if record_id and not record_id.startswith("SIM-"):
            issues.append(f"{case_id} uses a non-synthetic record id")
        if record_id in {"SIM-REC-001", "SIM-REC-002", "SIM-REC-003", "SIM-REC-004"} and record_id not in seed_ids:
            issues.append(f"{case_id} refers to a missing synthetic record")

    for case in cases:
        check_tool(case.get("case_id", "?"), case.get("gold", {}).get("expected_tool"))
        for turn in case.get("turns", []):
            check_tool(case.get("case_id", "?"), turn.get("expected_tool"))

    manifest_hash = hashlib.sha256(SOURCE_MANIFEST.read_bytes()).hexdigest()
    if frozen.get("source_manifest_sha256") != manifest_hash:
        issues.append("frozen source manifest hash does not match the current manifest")
    print(f"cases={len(cases)} categories={dict(category_counts)} source_count={len(source_ids)}")
    print(f"source_manifest_sha256={manifest_hash}")
    for issue in issues:
        print(f"ERROR: {issue}")
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
