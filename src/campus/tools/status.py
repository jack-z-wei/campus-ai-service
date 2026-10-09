"""SQLite-backed status and simulated human-service tools for synthetic users."""

from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid5
from zoneinfo import ZoneInfo

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATABASE = PROJECT_ROOT / "runs" / "campus_demo.sqlite3"
DEFAULT_SEED = PROJECT_ROOT / "data" / "campus" / "simulation_records.json"
USER_ID_PATTERN = re.compile(r"^SIM-USER-\d{3}$")
RECORD_ID_PATTERN = re.compile(r"^SIM-REC-\d{3}$")
IDEMPOTENCY_PATTERN = re.compile(r"^[A-Za-z0-9_-]{8,80}$")
ALLOWED_SERVICE_TYPES = {
    "aid_application",
    "scholarship_application",
    "dorm_repair",
    "library_service",
}
ALLOWED_TICKET_TYPES = {
    "dorm_repair_followup",
    "aid_application_followup",
    "library_service_followup",
    "general_student_service",
}


def _valid_simulated_user(user_id: str | None) -> bool:
    return isinstance(user_id, str) and USER_ID_PATTERN.fullmatch(user_id) is not None


def initialize_demo_database(
    db_path: Path = DEFAULT_DATABASE,
    *,
    seed_path: Path = DEFAULT_SEED,
) -> None:
    seed = json.loads(seed_path.read_text(encoding="utf-8"))
    if not seed.get("all_records_simulated") or not seed.get("not_real_student_records"):
        raise ValueError("Refusing to seed a database without an explicit synthetic-data marker.")

    db_path = db_path.resolve()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path, timeout=5) as connection:
        connection.execute(
            """CREATE TABLE IF NOT EXISTS application_status (
                record_id TEXT PRIMARY KEY,
                owner_user_id TEXT NOT NULL,
                service_type TEXT NOT NULL,
                status TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                public_note TEXT NOT NULL,
                simulation_only INTEGER NOT NULL CHECK (simulation_only = 1)
            )"""
        )
        connection.execute(
            """CREATE TABLE IF NOT EXISTS human_service_ticket (
                ticket_id TEXT PRIMARY KEY,
                requester_user_id TEXT NOT NULL,
                service_type TEXT NOT NULL,
                record_id TEXT,
                reason TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                idempotency_key TEXT NOT NULL,
                simulation_only INTEGER NOT NULL CHECK (simulation_only = 1),
                UNIQUE (requester_user_id, idempotency_key)
            )"""
        )
        for row in seed.get("records", []):
            record_id = row.get("record_id")
            owner_user_id = row.get("owner_user_id")
            if (
                not isinstance(record_id, str)
                or not RECORD_ID_PATTERN.fullmatch(record_id)
                or not _valid_simulated_user(owner_user_id)
                or row.get("service_type") not in ALLOWED_SERVICE_TYPES
            ):
                raise ValueError("Synthetic seed contains an invalid record or user identifier.")
            connection.execute(
                """INSERT OR IGNORE INTO application_status
                (record_id, owner_user_id, service_type, status, updated_at, public_note, simulation_only)
                VALUES (?, ?, ?, ?, ?, ?, 1)""",
                (
                    record_id,
                    owner_user_id,
                    row["service_type"],
                    row["status"],
                    row["updated_at"],
                    row["public_note"],
                ),
            )


class CampusStatusTools:
    """Tool service whose authenticated user ID is injected by trusted app code."""

    def __init__(self, db_path: Path = DEFAULT_DATABASE, *, seed_path: Path = DEFAULT_SEED) -> None:
        self.db_path = Path(db_path).resolve()
        initialize_demo_database(self.db_path, seed_path=seed_path)

    def query_application_status(
        self,
        *,
        authenticated_user_id: str | None,
        record_id: str,
        service_type: str | None = None,
    ) -> dict[str, Any]:
        if not _valid_simulated_user(authenticated_user_id):
            return {"outcome": "invalid_identity", "message": "请先完成身份验证后再查询。", "simulation_only": True}
        if not isinstance(record_id, str) or not RECORD_ID_PATTERN.fullmatch(record_id):
            return {"outcome": "invalid_record_id", "message": "记录编号格式无效。", "simulation_only": True}
        if service_type is not None and service_type not in ALLOWED_SERVICE_TYPES:
            return {"outcome": "invalid_service_type", "message": "服务类型无效。", "simulation_only": True}

        with sqlite3.connect(self.db_path, timeout=5) as connection:
            connection.row_factory = sqlite3.Row
            query = """SELECT record_id, service_type, status, updated_at, public_note, simulation_only
                FROM application_status WHERE record_id = ? AND owner_user_id = ?"""
            parameters: tuple[str, ...] = (record_id, authenticated_user_id)
            if service_type is not None:
                query += " AND service_type = ?"
                parameters += (service_type,)
            row = connection.execute(
                query,
                parameters,
            ).fetchone()
            if row is not None:
                return {
                    "outcome": "found",
                    "record_id": row["record_id"],
                    "service_type": row["service_type"],
                    "status": row["status"],
                    "updated_at": row["updated_at"],
                    "public_note": row["public_note"],
                    "simulation_only": bool(row["simulation_only"]),
                }

            other = connection.execute(
                "SELECT owner_user_id FROM application_status WHERE record_id = ?",
                (record_id,),
            ).fetchone()
        if other is not None and other["owner_user_id"] != authenticated_user_id:
            return {
                "outcome": "forbidden",
                "message": "没有可提供给当前账号的匹配记录。",
                "simulation_only": True,
            }
        return {"outcome": "not_found", "message": "未找到匹配的模拟记录。", "simulation_only": True}

    def create_human_service_request(
        self,
        *,
        authenticated_user_id: str | None,
        service_type: str,
        reason: str,
        idempotency_key: str,
        record_id: str | None = None,
    ) -> dict[str, Any]:
        if not _valid_simulated_user(authenticated_user_id):
            return {"outcome": "invalid_identity", "message": "请先完成身份验证后再提交。", "simulation_only": True}
        if service_type not in ALLOWED_TICKET_TYPES:
            return {"outcome": "invalid_service_type", "message": "服务类型无效。", "simulation_only": True}
        if not isinstance(reason, str) or not reason.strip() or len(reason) > 500:
            return {"outcome": "invalid_reason", "message": "请提供不超过500字的有效说明。", "simulation_only": True}
        if not isinstance(idempotency_key, str) or not IDEMPOTENCY_PATTERN.fullmatch(idempotency_key):
            return {"outcome": "invalid_idempotency_key", "message": "请求编号无效。", "simulation_only": True}
        if record_id is not None and (
            not isinstance(record_id, str) or not RECORD_ID_PATTERN.fullmatch(record_id)
        ):
            return {"outcome": "invalid_record_id", "message": "记录编号格式无效。", "simulation_only": True}

        with sqlite3.connect(self.db_path, timeout=5) as connection:
            connection.row_factory = sqlite3.Row
            prior = connection.execute(
                """SELECT ticket_id, service_type, record_id, reason, status, created_at
                FROM human_service_ticket
                WHERE requester_user_id = ? AND idempotency_key = ?""",
                (authenticated_user_id, idempotency_key),
            ).fetchone()
            if prior is not None:
                return self._ticket_result(prior, replay=True)

            if record_id is not None:
                linked = connection.execute(
                    "SELECT 1 FROM application_status WHERE record_id = ? AND owner_user_id = ?",
                    (record_id, authenticated_user_id),
                ).fetchone()
                if linked is None:
                    return {
                        "outcome": "record_unavailable",
                        "message": "没有可关联到当前账号的匹配模拟记录。",
                        "simulation_only": True,
                    }

            timestamp = datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds")
            ticket_id = "SIM-TICKET-" + uuid5(
                NAMESPACE_URL, f"campus-ticket:{authenticated_user_id}:{idempotency_key}"
            ).hex[:16]
            connection.execute(
                """INSERT INTO human_service_ticket
                (ticket_id, requester_user_id, service_type, record_id, reason, status,
                 created_at, idempotency_key, simulation_only)
                VALUES (?, ?, ?, ?, ?, 'created_simulated', ?, ?, 1)""",
                (
                    ticket_id,
                    authenticated_user_id,
                    service_type,
                    record_id,
                    reason.strip(),
                    timestamp,
                    idempotency_key,
                ),
            )
            row = connection.execute(
                """SELECT ticket_id, service_type, record_id, reason, status, created_at
                FROM human_service_ticket WHERE ticket_id = ?""",
                (ticket_id,),
            ).fetchone()
        return self._ticket_result(row, replay=False)

    @staticmethod
    def _ticket_result(row: sqlite3.Row, *, replay: bool) -> dict[str, Any]:
        return {
            "outcome": "created_simulated_ticket",
            "ticket_id": row["ticket_id"],
            "service_type": row["service_type"],
            "record_id": row["record_id"],
            "reason": row["reason"],
            "status": row["status"],
            "created_at": row["created_at"],
            "idempotent_replay": replay,
            "simulation_only": True,
            "real_human_contacted": False,
        }

