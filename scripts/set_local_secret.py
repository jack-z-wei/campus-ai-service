"""Set a local API secret without echoing it to the terminal."""

from __future__ import annotations

import getpass
from pathlib import Path


def main() -> None:
    env_path = Path(__file__).resolve().parents[1] / ".env"
    key = getpass.getpass("DEEPSEEK_API_KEY (input hidden): ").strip()
    if not key:
        raise SystemExit("No value entered; .env was not changed.")

    lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
    replacement = f"DEEPSEEK_API_KEY={key}"
    found = False
    updated: list[str] = []
    for line in lines:
        if line.startswith("DEEPSEEK_API_KEY="):
            if not found:
                updated.append(replacement)
                found = True
        else:
            updated.append(line)
    if not found:
        updated.append(replacement)

    env_path.write_text("\n".join(updated) + "\n", encoding="utf-8")
    print("Saved local .env value; secret omitted.")


if __name__ == "__main__":
    main()
