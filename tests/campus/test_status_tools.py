from __future__ import annotations

import json
from pathlib import Path

from campus.tools.status import CampusStatusTools


def test_frozen_status_tool_contract(tmp_path) -> None:
    contract_path = Path(__file__).resolve().parents[2] / "evaluation" / "status_tool_contract.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    service = CampusStatusTools(tmp_path / "campus.sqlite3")
    outcomes = {}
    for case in contract["cases"]:
        result = service.query_application_status(
            authenticated_user_id=case["authenticated_user_id"],
            **case["arguments"],
        )
        expected = case["expected"]
        assert result["outcome"] == expected["outcome"]
        if "status" in expected:
            assert result["status"] == expected["status"]
        if "simulation_only" in expected:
            assert result["simulation_only"] is expected["simulation_only"]
        outcomes[case["case_id"]] = result

    assert outcomes["ST01"]["status"] == "材料审核中"


def test_cross_user_status_query_returns_no_record_details(tmp_path) -> None:
    service = CampusStatusTools(tmp_path / "campus.sqlite3")
    result = service.query_application_status(
        authenticated_user_id="SIM-USER-001",
        record_id="SIM-REC-002",
        service_type="dorm_repair",
    )
    assert result["outcome"] == "forbidden"
    assert "status" not in result
    assert "owner_user_id" not in result
    assert "SIM-USER-002" not in json.dumps(result, ensure_ascii=False)


def test_status_query_can_resolve_service_type_from_owned_record_id(tmp_path) -> None:
    service = CampusStatusTools(tmp_path / "campus.sqlite3")
    result = service.query_application_status(
        authenticated_user_id="SIM-USER-001",
        record_id="SIM-REC-001",
    )

    assert result["outcome"] == "found"
    assert result["service_type"] == "aid_application"
    assert result["status"] == "材料审核中"
    assert result["simulation_only"] is True


def test_status_query_without_type_still_blocks_cross_user_record(tmp_path) -> None:
    service = CampusStatusTools(tmp_path / "campus.sqlite3")
    result = service.query_application_status(
        authenticated_user_id="SIM-USER-001",
        record_id="SIM-REC-002",
    )

    assert result["outcome"] == "forbidden"
    assert "status" not in result


def test_invalid_identifiers_do_not_modify_seed_data(tmp_path) -> None:
    service = CampusStatusTools(tmp_path / "campus.sqlite3")
    before = service.query_application_status(
        authenticated_user_id="SIM-USER-001",
        record_id="SIM-REC-001",
        service_type="aid_application",
    )
    bad_id = service.query_application_status(
        authenticated_user_id="SIM-USER-001",
        record_id="SIM-REC-001' OR 1=1 --",
        service_type="aid_application",
    )
    after = service.query_application_status(
        authenticated_user_id="SIM-USER-001",
        record_id="SIM-REC-001",
        service_type="aid_application",
    )
    assert bad_id["outcome"] == "invalid_record_id"
    assert before == after


def test_not_found_is_not_filled_with_an_invented_status(tmp_path) -> None:
    service = CampusStatusTools(tmp_path / "campus.sqlite3")
    result = service.query_application_status(
        authenticated_user_id="SIM-USER-001",
        record_id="SIM-REC-999",
        service_type="aid_application",
    )
    assert result["outcome"] == "not_found"
    assert "status" not in result

