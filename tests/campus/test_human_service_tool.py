from __future__ import annotations

import json
from pathlib import Path

from campus.tools.status import CampusStatusTools


def test_frozen_human_service_contract_and_persistence(tmp_path) -> None:
    contract_path = Path(__file__).resolve().parents[2] / "evaluation" / "human_service_contract.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    db_path = tmp_path / "campus.sqlite3"
    service = CampusStatusTools(db_path)
    results = {}
    for case in contract["cases"]:
        result = service.create_human_service_request(
            authenticated_user_id=case["authenticated_user_id"],
            **case["arguments"],
        )
        assert result["outcome"] == case["expected"]["outcome"]
        results[case["case_id"]] = result

    first = results["HS01"]
    replay = results["HS02"]
    assert first["ticket_id"] == replay["ticket_id"]
    assert first["idempotent_replay"] is False
    assert replay["idempotent_replay"] is True
    assert first["status"] == "created_simulated"
    assert first["simulation_only"] is True
    assert first["real_human_contacted"] is False
    assert results["HS03"]["outcome"] == "invalid_identity"
    assert results["HS04"]["outcome"] == "record_unavailable"

    persisted_service = CampusStatusTools(db_path)
    persisted = persisted_service.create_human_service_request(
        authenticated_user_id="SIM-USER-002",
        service_type="general_student_service",
        reason="重启后确认工单仍存在。",
        idempotency_key="HS05-REQUEST-001",
    )
    assert persisted["ticket_id"] == results["HS05"]["ticket_id"]
    assert persisted["idempotent_replay"] is True


def test_invalid_ticket_requests_create_nothing(tmp_path) -> None:
    service = CampusStatusTools(tmp_path / "campus.sqlite3")
    invalid_reason = service.create_human_service_request(
        authenticated_user_id="SIM-USER-001",
        service_type="general_student_service",
        reason="   ",
        idempotency_key="TEST-REQUEST-001",
    )
    invalid_key = service.create_human_service_request(
        authenticated_user_id="SIM-USER-001",
        service_type="general_student_service",
        reason="有效说明",
        idempotency_key="bad",
    )
    assert invalid_reason["outcome"] == "invalid_reason"
    assert invalid_key["outcome"] == "invalid_idempotency_key"

