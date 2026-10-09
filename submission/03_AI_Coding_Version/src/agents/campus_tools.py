"""Runtime-injected tools for the registered campus customer-service graph."""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Literal

from langchain_core.tools import BaseTool, tool
from langgraph.prebuilt import ToolRuntime

from campus.runtime import get_campus_knowledge_search, get_campus_status_tools
from campus.tools.status import USER_ID_PATTERN

KNOWLEDGE_SEARCH_TOP_K = 5
logger = logging.getLogger(__name__)


@tool
def search_campus_knowledge(
    query: str,
    runtime: ToolRuntime,
) -> str:
    """Search official campus source snapshots with date and scope metadata."""
    if not query.strip() or len(query) > 800:
        return json.dumps({"outcome": "invalid_query", "results": []}, ensure_ascii=False)
    try:
        result = get_campus_knowledge_search().search(query, top_k=KNOWLEDGE_SEARCH_TOP_K)
    except Exception as error:
        logger.exception(
            "Campus knowledge search failed (query_sha256=%s)",
            hashlib.sha256(query.encode("utf-8")).hexdigest()[:12],
        )
        return json.dumps(
            {"outcome": "search_unavailable", "error_type": type(error).__name__, "results": []},
            ensure_ascii=False,
        )
    payload = {
        "outcome": "ok" if result.hits else "no_evidence",
        "backend": result.backend,
        "results": [
            {
                "rank": hit.rank,
                "score": round(hit.score, 6),
                "source_id": hit.chunk.source_id,
                "title": hit.chunk.metadata.get("title"),
                "category": hit.chunk.metadata.get("category"),
                "url": hit.chunk.metadata.get("url"),
                "published_on": hit.chunk.metadata.get("published_on"),
                "scope": hit.chunk.metadata.get("scope"),
                "index_policy": hit.chunk.metadata.get("index_policy"),
                "text": hit.chunk.text,
            }
            for hit in result.hits
        ],
    }
    return json.dumps(payload, ensure_ascii=False)


@tool
def query_application_status(
    record_id: str,
    runtime: ToolRuntime,
    service_type: Literal[
        "aid_application", "scholarship_application", "dorm_repair", "library_service"
    ]
    | None = None,
) -> str:
    """Query the selected user's synthetic record; omit service_type rather than guessing."""
    configurable = runtime.config.get("configurable", {})
    simulation_user_id = configurable.get("simulation_user_id")
    result = get_campus_status_tools().query_application_status(
        authenticated_user_id=simulation_user_id,
        record_id=record_id,
        service_type=service_type,
    )
    return json.dumps(result, ensure_ascii=False)


@tool
def create_human_service_request(
    service_type: Literal[
        "dorm_repair_followup",
        "aid_application_followup",
        "library_service_followup",
        "general_student_service",
    ],
    reason: str,
    runtime: ToolRuntime,
    record_id: str | None = None,
) -> str:
    """Create a local demonstration ticket; no real staff member is contacted."""
    configurable = runtime.config.get("configurable", {})
    simulation_user_id = configurable.get("simulation_user_id")
    scope = ":".join(
        str(value)
        for value in (
            simulation_user_id or "",
            configurable.get("thread_id", ""),
            runtime.config.get("run_id", ""),
            runtime.tool_call_id or "",
            service_type,
            record_id or "",
            reason,
        )
    )
    idempotency_key = "agent-" + hashlib.sha256(scope.encode("utf-8")).hexdigest()[:40]
    result = get_campus_status_tools().create_human_service_request(
        authenticated_user_id=simulation_user_id,
        service_type=service_type,
        reason=reason,
        idempotency_key=idempotency_key,
        record_id=record_id,
    )
    return json.dumps(result, ensure_ascii=False)


CAMPUS_TOOLS = [search_campus_knowledge, query_application_status, create_human_service_request]


def tools_for_simulation_identity(simulation_user_id: object) -> list[BaseTool]:
    """Expose business tools only when a valid demo identity is configured."""
    if isinstance(simulation_user_id, str) and USER_ID_PATTERN.fullmatch(simulation_user_id):
        return CAMPUS_TOOLS
    return [search_campus_knowledge]
