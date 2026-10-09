"""Launch a localhost-only Windows API/UI preview with an isolated SQLite DB."""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODEL = "deepseek-flash"
API_URL = "http://127.0.0.1:8080"
UI_URL = "http://127.0.0.1:8501"


def require_free_port(port: int) -> None:
    with socket.socket() as sock:
        try:
            sock.bind(("127.0.0.1", port))
        except OSError as error:
            raise RuntimeError(f"127.0.0.1:{port} is already in use.") from error


def wait_for_http(url: str, process: subprocess.Popen, timeout: float = 45) -> tuple[int, str]:
    deadline = time.monotonic() + timeout
    last_error: str | None = None
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"Process {process.pid} exited with code {process.returncode}.")
        try:
            with urlopen(url, timeout=2) as response:
                return response.status, response.read(8192).decode("utf-8", errors="replace")
        except (URLError, TimeoutError, OSError) as error:
            last_error = type(error).__name__
            time.sleep(0.4)
    raise TimeoutError(f"{url} did not become ready in {timeout:g}s ({last_error}).")


def wait_for_existing_http(url: str, timeout: float = 10) -> tuple[int, str]:
    deadline = time.monotonic() + timeout
    last_error: str | None = None
    while time.monotonic() < deadline:
        try:
            with urlopen(url, timeout=2) as response:
                return response.status, response.read(8192).decode("utf-8", errors="replace")
        except (URLError, TimeoutError, OSError) as error:
            last_error = type(error).__name__
            time.sleep(0.3)
    raise TimeoutError(f"Existing service {url} was not reachable in {timeout:g}s ({last_error}).")


def stop(processes: list[subprocess.Popen]) -> None:
    for process in reversed(processes):
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    launch_mode = parser.add_mutually_exclusive_group()
    launch_mode.add_argument(
        "--backend-only",
        action="store_true",
        help="Start FastAPI only; leave Streamlit and the browser closed.",
    )
    launch_mode.add_argument(
        "--ui-only",
        action="store_true",
        help="Start Streamlit and attach to an existing FastAPI service.",
    )
    args = parser.parse_args()

    if sys.platform != "win32":
        raise SystemExit("Run with the Windows project .venv, not WSL Python.")

    if not args.ui_only:
        require_free_port(8080)
    if not args.backend_only:
        require_free_port(8501)

    run_prefix = "backend-preview" if args.backend_only else "ui-preview"
    run_id = datetime.now().astimezone().strftime(f"{run_prefix}-%Y%m%d-%H%M%S")
    run_dir = PROJECT_ROOT / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    api_log = run_dir / "api.log"
    ui_log = run_dir / "streamlit.log"
    sqlite_path = run_dir / "checkpoints.sqlite3"

    environment = os.environ.copy()
    environment.update(
        {
            "HOST": "127.0.0.1",
            "PORT": "8080",
            "DATABASE_TYPE": "sqlite",
            "SQLITE_DB_PATH": str(sqlite_path),
            "USE_FAKE_MODEL": "false",
            "DEFAULT_MODEL": MODEL,
            "AGENT_URL": API_URL,
            "STREAMLIT_SERVER_HEADLESS": "true",
            "STREAMLIT_SERVER_ADDRESS": "127.0.0.1",
            "STREAMLIT_SERVER_PORT": "8501",
            "STREAMLIT_BROWSER_GATHER_USAGE_STATS": "false",
        }
    )
    detached = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    processes: list[subprocess.Popen] = []
    manifest: dict = {
        "run_id": run_id,
        "started_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "api_url": API_URL,
        "ui_url": UI_URL,
        "model": MODEL,
        "fake_model": False,
        "api_started_by_launcher": not args.ui_only,
        "attached_to_existing_api": args.ui_only,
        "frontend_started": False,
        "sqlite_path": None if args.ui_only else str(sqlite_path),
        "synthetic_data_only": True,
        "course_result": False,
    }

    try:
        api: subprocess.Popen | None = None
        if args.ui_only:
            health_status, _ = wait_for_existing_http(f"{API_URL}/health")
            info_status, info_body = wait_for_existing_http(f"{API_URL}/info")
        else:
            with api_log.open("w", encoding="utf-8") as api_output:
                api = subprocess.Popen(
                    [sys.executable, "src/run_service.py"],
                    cwd=PROJECT_ROOT,
                    env=environment,
                    stdin=subprocess.DEVNULL,
                    stdout=api_output,
                    stderr=subprocess.STDOUT,
                    creationflags=detached,
                )
            processes.append(api)
            health_status, _ = wait_for_http(f"{API_URL}/health", api)
            info_status, info_body = wait_for_http(f"{API_URL}/info", api)
        info = json.loads(info_body)
        agent_keys = [agent.get("key") for agent in info.get("agents", [])]
        if info.get("default_model") != MODEL:
            raise RuntimeError(f"Unexpected API default model: {info.get('default_model')}.")
        if "campus-customer-service" not in agent_keys:
            raise RuntimeError("Campus customer-service agent is not registered.")

        if args.backend_only:
            assert api is not None
            manifest.update(
                {
                    "api_pid": api.pid,
                    "api_health_status": health_status,
                    "api_info_status": info_status,
                    "agent_count": len(agent_keys),
                    "ready": True,
                    "paid_chat_performed_by_launcher": False,
                    "api_log": str(api_log),
                }
            )
            manifest["finished_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
            manifest_path = run_dir / "manifest.json"
            manifest_path.write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            print(json.dumps(manifest, ensure_ascii=False, indent=2))
            print(f"manifest: {manifest_path}")
            return 0

        with ui_log.open("w", encoding="utf-8") as ui_output:
            ui = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "streamlit",
                    "run",
                    "src/streamlit_app.py",
                    "--server.address=127.0.0.1",
                    "--server.port=8501",
                    "--server.headless=true",
                ],
                cwd=PROJECT_ROOT,
                env=environment,
                stdin=subprocess.DEVNULL,
                stdout=ui_output,
                stderr=subprocess.STDOUT,
                creationflags=detached,
            )
        processes.append(ui)
        ui_health_status, _ = wait_for_http(f"{UI_URL}/_stcore/health", ui)
        page_status, page = wait_for_http(f"{UI_URL}/", ui)
        if "streamlit" not in page.lower():
            raise RuntimeError("Streamlit page shell was not returned.")

        manifest.update(
            {
                "streamlit_pid": ui.pid,
                "api_health_status": health_status,
                "api_info_status": info_status,
                "agent_count": len(agent_keys),
                "ui_health_status": ui_health_status,
                "ui_page_status": page_status,
                "frontend_started": True,
                "ready": True,
                "paid_chat_performed_by_launcher": False,
                "streamlit_log": str(ui_log),
            }
        )
        if api is not None:
            manifest["api_pid"] = api.pid
            manifest["api_log"] = str(api_log)
        try:
            os.startfile(UI_URL)  # type: ignore[attr-defined]
            manifest["browser_opened"] = True
        except OSError as error:
            manifest["browser_opened"] = False
            manifest["browser_open_error_type"] = type(error).__name__

        manifest["finished_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
        manifest_path = run_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
        print(f"manifest: {manifest_path}")
        return 0
    except Exception as error:
        stop(processes)
        manifest.update(
            {
                "ready": False,
                "error_type": type(error).__name__,
                "error": str(error),
                "finished_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            }
        )
        (run_dir / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
