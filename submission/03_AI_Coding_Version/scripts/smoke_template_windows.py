"""Exercise the upstream FastAPI service and Streamlit UI using the fake model.

This Windows-only, zero-cloud-cost smoke check is engineering evidence only. Its
response must never be reused as a campus answer or course model result.
"""

from __future__ import annotations

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


def free_local_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_for_http(url: str, process: subprocess.Popen, label: str, timeout: float = 30) -> tuple[int, str]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"{label} exited early with code {process.returncode}")
        try:
            with urlopen(url, timeout=1) as response:
                return response.status, response.read(4096).decode("utf-8", errors="replace")
        except (URLError, TimeoutError, OSError):
            time.sleep(0.25)
    raise TimeoutError(f"{label} did not become ready within {timeout:g} seconds")


def main() -> int:
    if sys.platform != "win32":
        raise SystemExit("Run this smoke check with the Windows project .venv.")

    sys.path.insert(0, str(PROJECT_ROOT / "src"))
    from streamlit.testing.v1 import AppTest

    from client import AgentClient

    port = free_local_port()
    ui_port = free_local_port()
    while ui_port == port:
        ui_port = free_local_port()
    base_url = f"http://127.0.0.1:{port}"
    ui_url = f"http://127.0.0.1:{ui_port}"
    run_id = datetime.now().astimezone().strftime("smoke-%Y%m%d-%H%M%S")
    run_dir = PROJECT_ROOT / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    log_path = run_dir / "service.log"
    streamlit_log_path = run_dir / "streamlit.log"
    result: dict = {
        "run_id": run_id,
        "mode": "test_fake",
        "course_result": False,
        "paid_api_request_performed": False,
        "base_url": base_url,
        "streamlit_url": ui_url,
        "started_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }

    environment = os.environ.copy()
    environment.update(
        {
            "HOST": "127.0.0.1",
            "PORT": str(port),
            "AGENT_URL": base_url,
            "USE_FAKE_MODEL": "true",
            "DEFAULT_MODEL": "fake",
            "DATABASE_TYPE": "sqlite",
            "SQLITE_DB_PATH": str(run_dir / "checkpoints.sqlite3"),
            "STREAMLIT_CLIENT_TOOLBARMODE": "minimal",
            "STREAMLIT_SERVER_HEADLESS": "true",
            "STREAMLIT_BROWSER_GATHER_USAGE_STATS": "false",
        }
    )
    # AppTest and the service subprocess share this process environment.
    os.environ.update(environment)

    service = None
    streamlit = None
    try:
        with (
            log_path.open("w", encoding="utf-8") as log_file,
            streamlit_log_path.open("w", encoding="utf-8") as streamlit_log,
        ):
            service = subprocess.Popen(
                [sys.executable, "src/run_service.py"],
                cwd=PROJECT_ROOT,
                env=environment,
                stdout=log_file,
                stderr=subprocess.STDOUT,
            )

            health_status, _ = wait_for_http(f"{base_url}/health", service, "FastAPI service")
            with urlopen(f"{base_url}/info", timeout=5) as response:
                info = json.loads(response.read().decode("utf-8"))

            streamlit = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "streamlit",
                    "run",
                    "src/streamlit_app.py",
                    "--server.address=127.0.0.1",
                    f"--server.port={ui_port}",
                    "--server.headless=true",
                ],
                cwd=PROJECT_ROOT,
                env=environment,
                stdout=streamlit_log,
                stderr=subprocess.STDOUT,
            )
            ui_health_status, _ = wait_for_http(
                f"{ui_url}/_stcore/health", streamlit, "Streamlit HTTP server"
            )
            ui_page_status, ui_html = wait_for_http(f"{ui_url}/", streamlit, "Streamlit page")
            legacy_health_status = None
            try:
                with urlopen(f"{ui_url}/healthz", timeout=3) as response:
                    legacy_health_status = response.status
            except URLError as error:
                legacy_health_status = getattr(error, "code", None)

            client = AgentClient(base_url=base_url, agent="chatbot", timeout=10)
            direct_answer = client.invoke(
                "Confirm the service is responding in fake-model smoke mode.", model="fake"
            )
            result["service"] = {
                "ready": True,
                "health_status": health_status,
                "agents": [agent["key"] for agent in info.get("agents", [])],
                "invoke_type": direct_answer.type,
                "invoke_answer": direct_answer.content,
            }

            campus_client = AgentClient(
                base_url=base_url, agent="campus-customer-service", timeout=10
            )
            campus_answer = campus_client.invoke(
                "演示接口连通检查。",
                model="fake",
                thread_id="campus-fake-smoke-thread",
                user_id="campus-fake-smoke-user",
                agent_config={"simulation_user_id": "SIM-USER-001"},
            )
            result["campus_agent"] = {
                "registered": "campus-customer-service" in result["service"]["agents"],
                "invoke_type": campus_answer.type,
                "invoke_answer": campus_answer.content,
                "simulation_config_request_accepted": campus_answer.type == "ai",
                "course_result": False,
            }

            ui = AppTest.from_file(str(PROJECT_ROOT / "src" / "streamlit_app.py")).run(timeout=20)
            if ui.exception:
                raise RuntimeError(f"Streamlit initial render failed: {ui.exception[0].message}")
            result["streamlit"] = {
                "rendered": True,
                "http_page_status": ui_page_status,
                "http_page_contains_streamlit_shell": "streamlit" in ui_html.lower(),
                "native_health_endpoint_status": ui_health_status,
                "healthz_endpoint_status": legacy_health_status,
                "chat_input_count": len(ui.chat_input),
                "sidebar_selectbox_count": len(ui.sidebar.selectbox),
                "sidebar_toggle_count": len(ui.sidebar.toggle),
                "initial_chat_message_count": len(ui.chat_message),
            }
            if not ui.chat_input:
                raise AssertionError("Streamlit rendered without a chat input")
            if ui.sidebar.toggle:
                ui.sidebar.toggle[0].set_value(False)
            if len(ui.sidebar.selectbox) > 1:
                ui.sidebar.selectbox[1].set_value("campus-customer-service")
            ui.run(timeout=20)
            if ui.exception:
                raise RuntimeError(
                    f"Campus agent settings render failed: {ui.exception[0].message}"
                )
            simulation_selectors = [
                selector for selector in ui.sidebar.selectbox if "模拟演示身份" in selector.label
            ]
            if not simulation_selectors:
                raise AssertionError(
                    "Campus UI did not show its clearly labeled demo identity selector"
                )
            simulation_selectors[0].set_value("SIM-USER-002")
            ui.chat_input[0].set_value(
                "Check that the selected campus agent reaches the service."
            ).run(timeout=20)
            if ui.exception:
                raise RuntimeError(f"Streamlit chat failed: {ui.exception[0].message}")
            rendered = [
                element.markdown[0].value
                for element in ui.chat_message
                if element.avatar == "assistant" and element.markdown
            ]
            if not rendered or "fake model" not in rendered[-1].lower():
                raise AssertionError("UI response did not contain the fake-model smoke result")
            result["streamlit"].update(
                {
                    "chat_connected_to_service": True,
                    "selected_agent": "campus-customer-service",
                    "demo_identity_selector_rendered": True,
                    "selected_demo_identity": "SIM-USER-002",
                    "assistant_response": rendered[-1],
                    "course_result": False,
                }
            )
    except Exception as error:  # save evidence even when the smoke check fails
        result["error"] = f"{type(error).__name__}: {error}"
    finally:
        for process in (streamlit, service):
            if process is not None and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
        result["processes_stopped"] = all(
            process is None or process.poll() is not None for process in (streamlit, service)
        )
        result["finished_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
        (run_dir / "manifest.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if "error" in result else 0


if __name__ == "__main__":
    raise SystemExit(main())
