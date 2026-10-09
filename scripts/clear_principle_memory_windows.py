"""Clear one principles-edition conversation from the local Windows SQLite memory."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATABASE = ROOT / "runs" / "principles_memory.sqlite3"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session-id", required=True, help="Conversation session to clear.")
    parser.add_argument(
        "--simulation-user-id",
        choices=("SIM-USER-001", "SIM-USER-002", "SIM-USER-003"),
        help="The synthetic identity that owns this conversation; omit only for anonymous sessions.",
    )
    parser.add_argument("--memory-db", type=Path, default=DEFAULT_DATABASE)
    args = parser.parse_args()

    if sys.platform != "win32":
        raise SystemExit("Run the principles memory command with the Windows project .venv.")

    sys.path.insert(0, str(ROOT / "src"))
    from campus.conversation_memory import PrincipleConversationMemory

    memory = PrincipleConversationMemory(args.memory_db)
    try:
        deleted = memory.clear(args.session_id, args.simulation_user_id)
    except PermissionError as error:
        print(json.dumps({"status": "forbidden", "message": str(error)}, ensure_ascii=False))
        return 2
    print(
        json.dumps(
            {
                "status": "cleared" if deleted else "not_found",
                "session_id": args.session_id,
                "simulation_user_id": args.simulation_user_id,
                "memory_db": str(args.memory_db.resolve()),
                "paid_api_request_performed": False,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
