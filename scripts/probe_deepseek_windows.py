"""Make one paid DeepSeek connectivity request and record provider usage on Windows."""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from langchain_core.messages import HumanMessage, SystemMessage

from core.llm import get_model
from core.settings import settings
from schema.models import DeepseekModelName


PRICE_URL = "https://api-docs.deepseek.com/zh-cn/quick_start/pricing/"
PEAK_INPUT_MISS_USD_PER_MILLION = 0.30
PEAK_INPUT_HIT_USD_PER_MILLION = 0.006
PEAK_OUTPUT_USD_PER_MILLION = 1.20


def as_int(value) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def append_jsonl(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def main() -> int:
    if sys.platform != "win32":
        raise SystemExit("Run this paid API probe with the Windows project venv.")
    if not settings.DEEPSEEK_API_KEY:
        raise SystemExit("DEEPSEEK_API_KEY is not configured; no request was made.")
    if settings.DEEPSEEK_MODEL != "deepseek-flash":
        raise SystemExit("Probe is pinned to the official deepseek-flash model.")

    run_id = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("api-smoke-%Y%m%d-%H%M%S")
    run_dir = ROOT / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    started = datetime.now(ZoneInfo("Asia/Shanghai"))
    prompt = "请只回复：校园客服 API 连通。"
    manifest = {
        "run_id": run_id,
        "purpose": "DeepSeek connectivity smoke; not a course question result",
        "started_at": started.isoformat(timespec="seconds"),
        "platform": sys.platform,
        "model": settings.DEEPSEEK_MODEL,
        "base_url": settings.DEEPSEEK_BASE_URL,
        "requested_max_tokens": 32,
        "max_retries": 0,
        "paid_api_request_performed": False,
        "course_result": False,
        "response": None,
        "usage": None,
        "estimated_cost_usd": None,
        "pricing_basis": "DeepSeek official peak rates; conservative estimate, all uncached input assumed",
        "pricing_source": PRICE_URL,
        "error_type": None,
        "error_status_code": None,
    }
    usage_record = {
        "run_id": run_id,
        "purpose": manifest["purpose"],
        "timestamp": started.isoformat(timespec="seconds"),
        "provider": "deepseek",
        "model": settings.DEEPSEEK_MODEL,
        "paid_api_request_count": 1,
        "status": "started",
        "prompt_tokens": None,
        "completion_tokens": None,
        "cached_input_tokens": None,
        "estimated_cost_usd": None,
        "estimate_basis": manifest["pricing_basis"],
        "pricing_source": PRICE_URL,
    }

    # get_model is configured with timeout=30 and max_retries=0.
    append_jsonl(
        ROOT / "reports" / "API_REQUEST_EVENTS.jsonl",
        {
            "run_id": run_id,
            "event": "request_started",
            "timestamp": started.isoformat(timespec="seconds"),
            "model": settings.DEEPSEEK_MODEL,
            "paid_api_request_count": 1,
        },
    )
    try:
        model = get_model(DeepseekModelName.DEEPSEEK_FLASH).bind(max_tokens=32)
        response = model.invoke(
            [
                SystemMessage(content="只输出指定短句，不要解释。"),
                HumanMessage(content=prompt),
            ],
            config={"run_name": run_id, "tags": ["paid-api-smoke", "not-course-result"]},
        )

        response_metadata = getattr(response, "response_metadata", {}) or {}
        usage_metadata = getattr(response, "usage_metadata", {}) or {}
        provider_usage = response_metadata.get("token_usage") or response_metadata.get("usage") or {}
        prompt_details = provider_usage.get("prompt_tokens_details") or {}
        input_details = usage_metadata.get("input_token_details") or {}
        input_tokens = as_int(usage_metadata.get("input_tokens", provider_usage.get("prompt_tokens")))
        output_tokens = as_int(
            usage_metadata.get("output_tokens", provider_usage.get("completion_tokens"))
        )
        cached_tokens = as_int(
            prompt_details.get("cached_tokens", input_details.get("cache_read", 0))
        ) or 0
        cached_tokens = min(cached_tokens, input_tokens or 0)
        total_tokens = as_int(usage_metadata.get("total_tokens", provider_usage.get("total_tokens")))

        estimated_cost = None
        if input_tokens is not None and output_tokens is not None:
            uncached_tokens = max(0, input_tokens - cached_tokens)
            estimated_cost = round(
                (uncached_tokens * PEAK_INPUT_MISS_USD_PER_MILLION
                 + cached_tokens * PEAK_INPUT_HIT_USD_PER_MILLION
                 + output_tokens * PEAK_OUTPUT_USD_PER_MILLION)
                / 1_000_000,
                10,
            )

        manifest.update(
            {
                "paid_api_request_performed": True,
                "response": str(response.content),
                "usage": {
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": total_tokens,
                    "cached_input_tokens": cached_tokens,
                    "raw_usage_metadata": usage_metadata,
                },
                "estimated_cost_usd": estimated_cost,
                "observed_output_exceeded_requested_max_tokens": (
                    output_tokens is not None and output_tokens > 32
                ),
                "response_model": response_metadata.get("model_name") or response_metadata.get("model"),
                "finish_reason": response_metadata.get("finish_reason"),
            }
        )
        usage_record.update(
            {
                "status": "succeeded",
                "prompt_tokens": input_tokens,
                "completion_tokens": output_tokens,
                "total_tokens": total_tokens,
                "cached_input_tokens": cached_tokens,
                "estimated_cost_usd": estimated_cost,
            }
        )
        return_code = 0
    except Exception as exc:
        # Store only exception type and HTTP status. Never serialize request/response headers.
        status_code = getattr(exc, "status_code", None)
        manifest.update({"error_type": type(exc).__name__, "error_status_code": status_code})
        usage_record.update(
            {"status": "failed", "error_type": type(exc).__name__, "error_status_code": status_code}
        )
        return_code = 1
    finally:
        finished = datetime.now(ZoneInfo("Asia/Shanghai"))
        manifest["finished_at"] = finished.isoformat(timespec="seconds")
        manifest["duration_seconds"] = round((finished - started).total_seconds(), 3)
        (run_dir / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        usage_record["timestamp_finished"] = finished.isoformat(timespec="seconds")
        append_jsonl(
            ROOT / "reports" / "API_REQUEST_EVENTS.jsonl",
            {
                "run_id": run_id,
                "event": "request_finished",
                "timestamp": finished.isoformat(timespec="seconds"),
                "status": usage_record["status"],
                "error_type": usage_record.get("error_type"),
                "error_status_code": usage_record.get("error_status_code"),
            },
        )
        append_jsonl(ROOT / "reports" / "API_USAGE.jsonl", usage_record)
    print(
        json.dumps(
            {
                "run_id": run_id,
                "status": usage_record["status"],
                "paid_api_request_performed": manifest["paid_api_request_performed"],
                "usage": manifest.get("usage"),
                "estimated_cost_usd": manifest.get("estimated_cost_usd"),
                "error_type": manifest.get("error_type"),
                "error_status_code": manifest.get("error_status_code"),
            },
            ensure_ascii=False,
        )
    )
    return return_code


if __name__ == "__main__":
    raise SystemExit(main())
