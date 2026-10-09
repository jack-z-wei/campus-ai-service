"""Record a privacy-safe Windows/Ollama environment check.

Run this with Windows Python from the project directory. No cloud API is called,
and neither environment secrets nor embedding values are written to the report.
"""

from __future__ import annotations

import argparse
import json
import math
import platform
import sys
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = PROJECT_ROOT / "reports" / "WINDOWS_ENVIRONMENT.json"


def read_local_env_value(name: str) -> str:
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        return ""
    for line in env_path.read_text(encoding="utf-8").splitlines():
        key, separator, value = line.partition("=")
        if separator and key.strip() == name:
            return value.strip().strip("\"'")
    return ""


def post_json(url: str, payload: dict, timeout: float = 20) -> dict:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def get_json(url: str, timeout: float = 5) -> dict:
    with urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--require-venv",
        action="store_true",
        help="fail unless this process is running inside the project virtual environment",
    )
    args = parser.parse_args()

    report = {
        "checked_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "python": {
            "executable": sys.executable,
            "platform": sys.platform,
            "version": platform.python_version(),
            "system": platform.system(),
            "architecture": platform.machine(),
            "in_virtual_environment": sys.prefix != sys.base_prefix,
            "virtual_environment_prefix": sys.prefix if sys.prefix != sys.base_prefix else None,
        },
        "ollama": {"base_url": "http://127.0.0.1:11434", "available": False},
        "embedding": {"model": "bge-m3:latest", "inference_succeeded": False},
        "credentials": {
            "env_file_exists": (PROJECT_ROOT / ".env").exists(),
            "deepseek_key_configured": bool(read_local_env_value("DEEPSEEK_API_KEY")),
            "key_value_recorded": False,
        },
        "paid_api_request_performed": False,
        "errors": [],
    }

    errors: list[str] = report["errors"]
    if sys.platform != "win32":
        errors.append(f"Expected Windows Python (win32), got {sys.platform!r}.")
    if args.require_venv and not report["python"]["in_virtual_environment"]:
        errors.append("This check requires the project virtual environment.")

    base_url = report["ollama"]["base_url"]
    try:
        tags = get_json(f"{base_url}/api/tags")
        models = tags.get("models", [])
        model = next((item for item in models if item.get("name") == "bge-m3:latest"), None)
        report["ollama"]["available"] = True
        report["ollama"]["model_present"] = model is not None
        if model is not None:
            report["ollama"]["reported_embedding_length"] = model.get("details", {}).get(
                "embedding_length"
            )
            try:
                result = post_json(
                    f"{base_url}/api/embed",
                    {
                        "model": "bge-m3:latest",
                        "input": ["长安大学图书馆开放时间和借阅规则"],
                        "truncate": False,
                    },
                )
                vectors = result.get("embeddings", [])
                vector = vectors[0] if vectors else []
                valid = bool(vector) and all(
                    isinstance(value, (int, float)) and math.isfinite(value)
                    for value in vector
                )
                report["embedding"].update(
                    {
                        "inference_succeeded": valid,
                        "vector_count": len(vectors),
                        "dimension": len(vector),
                        "all_values_finite": valid,
                        "sample_text_recorded": False,
                        "vector_values_recorded": False,
                    }
                )
                if not valid:
                    errors.append("Ollama returned no embedding or a non-finite vector.")
                elif model.get("details", {}).get("embedding_length") not in (None, len(vector)):
                    errors.append(
                        "Embedding inference dimension differs from model metadata: "
                        f"{len(vector)} vs {model['details'].get('embedding_length')}."
                    )
            except (HTTPError, URLError, TimeoutError, OSError, ValueError) as error:
                errors.append(f"Embedding request failed: {type(error).__name__}: {error}")
        else:
            errors.append("Ollama is reachable, but bge-m3:latest is not in its model list.")
    except (HTTPError, URLError, TimeoutError, OSError, ValueError) as error:
        errors.append(f"Ollama model-list request failed: {type(error).__name__}: {error}")

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
