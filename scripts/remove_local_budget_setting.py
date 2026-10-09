"""Remove an obsolete local budget environment variable without showing .env."""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    if sys.platform != "win32":
        raise SystemExit("Run this local configuration edit with Windows Python.")
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if not env_path.exists():
        print("Local .env is absent; no edit made.")
        return 0
    lines = env_path.read_text(encoding="utf-8").splitlines()
    filtered = [line for line in lines if not line.startswith("API_BUDGET_CNY=")]
    removed = len(lines) - len(filtered)
    if removed:
        env_path.write_text("\n".join(filtered) + "\n", encoding="utf-8")
    print(f"Removed obsolete API_BUDGET_CNY setting: {bool(removed)}. Other values were not displayed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
