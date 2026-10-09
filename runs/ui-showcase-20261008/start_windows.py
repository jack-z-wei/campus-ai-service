from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.request import urlopen

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUN_DIR = Path(__file__).resolve().parent
API_PORT = 8081
UI_PORT = 8502
API_URL = f"http://127.0.0.1:{API_PORT}"
UI_URL = f"http://127.0.0.1:{UI_PORT}"
MODEL = "deepseek-flash"


def require_free_port(port: int) -> None:
    with socket.socket() as sock:
        try:
            sock.bind(("127.0.0.1", port))
        except OSError as error:
            raise RuntimeError(f"127.0.0.1:{port} is already in use") from error


def wait_http(url: str, process: subprocess.Popen, timeout: float = 60) -> tuple[int, str]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"Process {process.pid} exited with code {process.returncode}")
        try:
            with urlopen(url, timeout=3) as response:
                return response.status, response.read(8192).decode("utf-8", errors="replace")
        except Exception:
            time.sleep(0.5)
    raise TimeoutError(f"{url} did not become ready within {timeout:g}s")


def main() -> int:
    if sys.platform != "win32":
        raise SystemExit("Run with the Windows project .venv, not WSL Python.")
    require_free_port(API_PORT)
    require_free_port(UI_PORT)
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update(
        {
            "HOST": "127.0.0.1",
            "PORT": str(API_PORT),
            "USE_FAKE_MODEL": "false",
            "DEFAULT_MODEL": MODEL,
            "DATABASE_TYPE": "sqlite",
            "SQLITE_DB_PATH": str(RUN_DIR / "checkpoints.sqlite3"),
            "AGENT_URL": API_URL,
            "STREAMLIT_SERVER_HEADLESS": "true",
            "STREAMLIT_SERVER_ADDRESS": "127.0.0.1",
            "STREAMLIT_SERVER_PORT": str(UI_PORT),
            "STREAMLIT_BROWSER_GATHER_USAGE_STATS": "false",
        }
    )
    probe = subprocess.run(
        [
            sys.executable,
            "-c",
            "import json,sys; sys.path.insert(0,'src'); from core.settings import settings; print(json.dumps({'fake_model': settings.USE_FAKE_MODEL, 'default_model': str(settings.DEFAULT_MODEL), 'deepseek_key_configured': bool(settings.DEEPSEEK_API_KEY)}))",
        ],
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    provider = json.loads(probe.stdout.strip().splitlines()[-1])
    if provider != {
        "fake_model": False,
        "default_model": MODEL,
        "deepseek_key_configured": True,
    }:
        raise RuntimeError(f"Real-model preflight failed: {provider}")

    detached = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    processes: list[subprocess.Popen] = []
    started = datetime.now().astimezone().isoformat(timespec="seconds")
    try:
        with (RUN_DIR / "api.log").open("w", encoding="utf-8") as log:
            api = subprocess.Popen(
                [sys.executable, "src/run_service.py"],
                cwd=PROJECT_ROOT,
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=subprocess.STDOUT,
                creationflags=detached,
            )
        processes.append(api)
        health_status, _ = wait_http(f"{API_URL}/health", api)
        info_status, info_text = wait_http(f"{API_URL}/info", api)
        info = json.loads(info_text)
        if info.get("default_model") != MODEL or "campus-customer-service" not in {
            item.get("key") for item in info.get("agents", [])
        }:
            raise RuntimeError("The real campus Agent was not registered with the expected model")

        with (RUN_DIR / "streamlit.log").open("w", encoding="utf-8") as log:
            ui = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "streamlit",
                    "run",
                    "src/streamlit_app.py",
                    f"--server.address=127.0.0.1",
                    f"--server.port={UI_PORT}",
                    "--server.headless=true",
                ],
                cwd=PROJECT_ROOT,
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=subprocess.STDOUT,
                creationflags=detached,
            )
        processes.append(ui)
        ui_health_status, _ = wait_http(f"{UI_URL}/_stcore/health", ui)
        page_status, page = wait_http(f"{UI_URL}/", ui)
        if "streamlit" not in page.lower():
            raise RuntimeError("Streamlit page shell was not returned")
        manifest = {
            "run_id": RUN_DIR.name,
            "started_at": started,
            "platform": "win32",
            "api_url": API_URL,
            "ui_url": UI_URL,
            "model": MODEL,
            "fake_model": False,
            "deepseek_key_configured": True,
            "isolated_sqlite_path": str(RUN_DIR / "checkpoints.sqlite3"),
            "api_pid": api.pid,
            "ui_pid": ui.pid,
            "api_health_status": health_status,
            "api_info_status": info_status,
            "ui_health_status": ui_health_status,
            "ui_page_status": page_status,
            "paid_chat_performed_by_launcher": False,
            "ready": True,
            "stop_processes_after_capture": [api.pid, ui.pid],
        }
        (RUN_DIR / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        try:
            os.startfile(UI_URL)  # type: ignore[attr-defined]
            manifest["browser_opened"] = True
        except OSError:
            manifest["browser_opened"] = False
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
        return 0
    except Exception:
        for process in reversed(processes):
            if process.poll() is None:
                process.terminate()
        raise


if __name__ == "__main__":
    raise SystemExit(main())
