"""Validate current Coze evidence and its Windows submission copy without network calls."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
COZE_ROOT = PROJECT_ROOT / "coze"
SUBMISSION_ROOT = PROJECT_ROOT / "submission"
SUBMISSION_COZE_ROOT = SUBMISSION_ROOT / "01_Coze_Version" / "coze"


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    if sys.platform != "win32":
        raise SystemExit("Run this package check with the Windows project .venv.")

    source_manifest = load_json(COZE_ROOT / "package_manifest.json")
    submission_manifest = load_json(SUBMISSION_ROOT / "package_manifest.json")
    if source_manifest.get("status") != "platform_tested_with_declared_limits":
        raise AssertionError("The Coze evidence manifest does not describe the actual platform run.")
    if source_manifest.get("coze_course_deliverables_met") is not True:
        raise AssertionError("The H-02 technical delivery checklist is not marked complete.")
    if (source_manifest.get("coze_acceptance_case_count"), source_manifest.get("coze_acceptance_assistant_turn_count")) != (14, 16):
        raise AssertionError("The frozen Coze run count must remain 14 cases / 16 assistant turns.")
    if (source_manifest.get("coze_partial_case_count"), source_manifest.get("coze_nonexecuted_frozen_case_count")) != (5, 7):
        raise AssertionError("The original partial and unexecuted Coze cases are not recorded correctly.")
    if (source_manifest.get("coze_supplemental_retest_count"), source_manifest.get("coze_supplemental_retest_pass_count"), source_manifest.get("coze_supplemental_retest_partial_count")) != (3, 1, 2):
        raise AssertionError("The supplemental prompt retest summary is not 3 / 1 pass / 2 partial.")
    if source_manifest.get("coze_prompt_platform_roundtrip_verified") is not True:
        raise AssertionError("The current prompt has not been verified against the saved platform copy.")

    prompt = (COZE_ROOT / "instructions.txt").read_text(encoding="utf-8-sig").strip()
    platform_copy = (COZE_ROOT / "logs" / "platform-prompt-updated-20261008.txt").read_text(encoding="utf-8-sig").strip()
    if prompt != platform_copy:
        raise AssertionError("The project prompt differs from the platform copy.")

    with (COZE_ROOT / "results.csv").open(encoding="utf-8-sig", newline="") as handle:
        frozen_rows = list(csv.DictReader(handle))
    if len(frozen_rows) != 21 or sum(bool(row["actual_answer"]) for row in frozen_rows) != 14:
        raise AssertionError("The frozen result table must retain 14 executed and 7 unexecuted rows.")
    if sum(row["execution_status"] == "partial_pass" for row in frozen_rows) != 5:
        raise AssertionError("The original five partial results must remain in the frozen table.")

    with (COZE_ROOT / "retests" / "20261008" / "retests.csv").open(encoding="utf-8-sig", newline="") as handle:
        reruns = list(csv.DictReader(handle))
    if len(reruns) != 3 or {row["frozen_case_id"] for row in reruns} != {"K01", "K06", "K09"}:
        raise AssertionError("The three prompt revision reruns are not present.")
    expected_statuses = {"K01": "partial_pass", "K06": "partial_pass", "K09": "pass"}
    if {row["frozen_case_id"]: row["execution_status"] for row in reruns} != expected_statuses:
        raise AssertionError("The supplemental rerun results differ from their recorded outcomes.")

    source_images = {path.name for path in (COZE_ROOT / "screenshots").glob("*.png")}
    package_images = {path.name for path in (SUBMISSION_COZE_ROOT / "screenshots").glob("*.png")}
    if source_images != package_images or not {row["screenshot"].split("/")[-1] for row in reruns} <= package_images:
        raise AssertionError("Coze screenshots are missing from or differ in the handoff copy.")

    file_rows = submission_manifest.get("files", [])
    if len(file_rows) != submission_manifest.get("file_count"):
        raise AssertionError("Submission file_count differs from its SHA-256 manifest.")
    for row in file_rows:
        path = SUBMISSION_ROOT / str(row["path"])
        raw = path.read_bytes()
        if len(raw) != row["size_bytes"] or hashlib.sha256(raw).hexdigest() != row["sha256"]:
            raise AssertionError(f"Submission manifest mismatch: {row['path']}.")
        if re.search(rb"sk-[A-Za-z0-9]{20,}", raw):
            if Path(row["path"]).name != ".env.example":
                raise AssertionError(f"Credential-like value in submission: {row['path']}.")
    if submission_manifest.get("directory_count") != 6 or submission_manifest.get("contains_dotenv") is not False:
        raise AssertionError("The six-folder submission manifest or secret exclusion flag is incorrect.")
    if submission_manifest.get("coze_course_deliverables_met") is not True:
        raise AssertionError("The generated handoff does not carry the H-02 completion status.")

    result = {
        "coze_source_status": source_manifest["status"],
        "frozen_cases": len(frozen_rows),
        "frozen_executed_cases": sum(bool(row["actual_answer"]) for row in frozen_rows),
        "frozen_partial_cases": 5,
        "supplemental_retests": len(reruns),
        "supplemental_outcomes": expected_statuses,
        "platform_prompt_roundtrip_verified": True,
        "coze_screenshots_copied": len(package_images),
        "submission_files_sha256_verified": len(file_rows),
        "submission_directories": submission_manifest["directory_count"],
        "contains_dotenv": submission_manifest["contains_dotenv"],
        "teacher_acceptance_claimed": submission_manifest["coze_teacher_acceptance_claimed"],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
