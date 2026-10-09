"""Exercise the campus chat through Streamlit AppTest against the live service."""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUN_DIR = Path(__file__).resolve().parent


def main() -> int:
    if sys.platform != "win32":
        raise SystemExit("Run with the Windows project .venv.")
    os.environ["AGENT_URL"] = "http://127.0.0.1:8080"
    sys.path.insert(0, str(PROJECT_ROOT / "src"))
    from streamlit.testing.v1 import AppTest

    question = "请查询我的模拟助学申请记录 SIM-REC-001，告诉我状态和更新时间。"
    manifest: dict = {
        "started_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "mode": "live_streamlit_app_test_synthetic_user",
        "course_result": False,
        "synthetic_data_only": True,
        "model_usage_available_from_service_response": False,
        "estimated_cost_usd": None,
        "note": "Current chat API response does not expose provider token usage.",
        "agent_url": "http://127.0.0.1:8080",
        "model": "deepseek-flash",
        "question": question,
        "simulation_user_id": "SIM-USER-001",
    }
    started = time.monotonic()
    try:
        app = AppTest.from_file(str(PROJECT_ROOT / "src" / "streamlit_app.py")).run(
            timeout=45
        )
        if app.exception:
            raise RuntimeError(f"Initial page render failed: {app.exception[0].message}")

        model = next(item for item in app.sidebar.selectbox if item.label == "LLM to use")
        model.set_value("deepseek-flash")
        agent = next(
            item for item in app.sidebar.selectbox if item.label == "Agent to use"
        )
        agent.set_value("campus-customer-service")
        stream_toggle = next(
            item for item in app.sidebar.toggle if item.label == "Stream results"
        )
        stream_toggle.set_value(False)
        app.run(timeout=45)
        if app.exception:
            raise RuntimeError(f"Campus agent settings render failed: {app.exception[0].message}")

        identity = next(
            item
            for item in app.sidebar.selectbox
            if item.label == "模拟演示身份（不对应真实账号）"
        )
        identity.set_value("SIM-USER-001")
        app.run(timeout=45)
        if app.exception:
            raise RuntimeError(f"Synthetic identity selection failed: {app.exception[0].message}")

        app.chat_input[0].set_value(question).run(timeout=150)
        if app.exception:
            raise RuntimeError(f"Live UI request failed: {app.exception[0].message}")

        assistant_messages = [
            {
                "avatar": item.avatar,
                "text": "\n".join(
                    element.value
                    for element in item.markdown
                    if isinstance(element.value, str)
                ),
            }
            for item in app.chat_message
            if item.avatar in ("ai", "assistant") and item.markdown
        ]
        answer = next(
            (item["text"] for item in reversed(assistant_messages) if item["text"]),
            "",
        )
        if not answer:
            raise AssertionError("No assistant answer was rendered in the chat UI.")

        manifest.update(
            {
                "completed": True,
                "selected_model": "deepseek-flash",
                "selected_agent": "campus-customer-service",
                "selected_synthetic_identity": "SIM-USER-001",
                "assistant_message_rendered": True,
                "assistant_answer": answer,
                "tool_status_elements": [
                    getattr(item, "label", "") for item in getattr(app, "status", [])
                ],
            }
        )
    except Exception as error:
        manifest["error_type"] = type(error).__name__
        manifest["error"] = str(error)
        manifest["completed"] = False
    finally:
        manifest["elapsed_seconds"] = round(time.monotonic() - started, 3)
        manifest["finished_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
        (RUN_DIR / "live-ui-app-test.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0 if manifest.get("completed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
