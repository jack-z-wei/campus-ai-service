"""Explicit schema, registry and executor for the standalone principles Agent."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from campus.context_expansion import expand_top_hit_continuation
from campus.knowledge import CampusKnowledgeSearch
from campus.tools.status import USER_ID_PATTERN, CampusStatusTools


class StrictToolInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class KnowledgeSearchInput(StrictToolInput):
    query: str = Field(min_length=1, max_length=800)


class StatusQueryInput(StrictToolInput):
    record_id: str = Field(pattern=r"^SIM-REC-\d{3}$")
    service_type: (
        Literal["aid_application", "scholarship_application", "dorm_repair", "library_service"]
        | None
    ) = None


class HumanRequestInput(StrictToolInput):
    service_type: Literal[
        "dorm_repair_followup",
        "aid_application_followup",
        "library_service_followup",
        "general_student_service",
    ]
    reason: str = Field(min_length=1, max_length=500)
    record_id: str | None = Field(default=None, pattern=r"^SIM-REC-\d{3}$")


@dataclass(frozen=True, slots=True)
class ToolExecutionContext:
    knowledge_search: CampusKnowledgeSearch
    status_tools: CampusStatusTools
    authenticated_user_id: str | None
    request_id: str


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    name: str
    description: str
    input_model: type[StrictToolInput]
    execute: Callable[[dict[str, Any], ToolExecutionContext], dict[str, Any]]

    def as_openai_tool(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.input_model.model_json_schema(),
            },
        }


def _search_knowledge(arguments: dict[str, Any], context: ToolExecutionContext) -> dict[str, Any]:
    result = context.knowledge_search.search(arguments["query"], top_k=5)
    evidence, expansions = expand_top_hit_continuation(result.hits, context.knowledge_search.chunks)
    return {
        "outcome": "ok" if result.hits else "no_evidence",
        "backend": result.backend,
        "context_expansions": expansions,
        "results": [
            {
                "rank": item.retrieval_rank,
                "score": round(item.cosine_score, 6) if item.cosine_score is not None else None,
                "source_id": item.chunk.source_id,
                "title": item.chunk.metadata.get("title"),
                "url": item.chunk.metadata.get("url"),
                "published_on": item.chunk.metadata.get("published_on"),
                "scope": item.chunk.metadata.get("scope"),
                "index_policy": item.chunk.metadata.get("index_policy"),
                "text": item.chunk.text,
                "context_expansion": item.chunk.metadata.get("context_expansion"),
            }
            for item in evidence
        ],
    }


def _query_status(arguments: dict[str, Any], context: ToolExecutionContext) -> dict[str, Any]:
    return context.status_tools.query_application_status(
        authenticated_user_id=context.authenticated_user_id,
        record_id=arguments["record_id"],
        service_type=arguments["service_type"],
    )


def _create_human_request(
    arguments: dict[str, Any], context: ToolExecutionContext
) -> dict[str, Any]:
    scope = ":".join(
        (
            context.authenticated_user_id or "",
            context.request_id,
            arguments["service_type"],
            arguments["record_id"] or "",
            arguments["reason"],
        )
    )
    idempotency_key = "agent-" + hashlib.sha256(scope.encode("utf-8")).hexdigest()[:40]
    return context.status_tools.create_human_service_request(
        authenticated_user_id=context.authenticated_user_id,
        service_type=arguments["service_type"],
        reason=arguments["reason"],
        idempotency_key=idempotency_key,
        record_id=arguments["record_id"],
    )


class ToolRegistry:
    """Validate model arguments and dispatch only to the fixed campus tool set."""

    def __init__(self) -> None:
        definitions = [
            ToolDefinition(
                name="search_campus_knowledge",
                description=(
                    "Search official campus source snapshots. Use this for campus policy; "
                    "the result includes dates, scope and source citations."
                ),
                input_model=KnowledgeSearchInput,
                execute=_search_knowledge,
            ),
            ToolDefinition(
                name="query_application_status",
                description=(
                    "Query one synthetic service record owned by the authenticated demo user. "
                    "If the user did not state a service type, omit service_type so the server "
                    "resolves the record within this user's own records. Never infer identity."
                ),
                input_model=StatusQueryInput,
                execute=_query_status,
            ),
            ToolDefinition(
                name="create_human_service_request",
                description=(
                    "Create a local synthetic service ticket only after the user explicitly "
                    "requests human service. No real staff member is contacted."
                ),
                input_model=HumanRequestInput,
                execute=_create_human_request,
            ),
        ]
        self._definitions = {definition.name: definition for definition in definitions}

    @property
    def definitions(self) -> list[dict[str, Any]]:
        return [definition.as_openai_tool() for definition in self._definitions.values()]

    def definitions_for(self, authenticated_user_id: str | None) -> list[dict[str, Any]]:
        """Do not advertise status or ticket tools without a valid demo identity."""
        if isinstance(authenticated_user_id, str) and USER_ID_PATTERN.fullmatch(
            authenticated_user_id
        ):
            return self.definitions
        return [self._definitions["search_campus_knowledge"].as_openai_tool()]

    def execute(
        self, name: str, arguments_json: str, context: ToolExecutionContext
    ) -> dict[str, Any]:
        definition = self._definitions.get(name)
        if definition is None:
            return {"outcome": "unknown_tool", "message": "Requested tool is not registered."}
        try:
            raw_arguments = json.loads(arguments_json)
            if not isinstance(raw_arguments, dict):
                return {
                    "outcome": "invalid_arguments",
                    "message": "Tool arguments must be an object.",
                }
            arguments = definition.input_model.model_validate(raw_arguments).model_dump()
        except (json.JSONDecodeError, ValidationError, TypeError) as error:
            return {
                "outcome": "invalid_arguments",
                "message": "Tool arguments did not match the registered schema.",
                "error_type": type(error).__name__,
            }

        try:
            return definition.execute(arguments, context)
        except Exception as error:
            return {
                "outcome": "tool_execution_error",
                "message": "The campus tool could not complete this request.",
                "error_type": type(error).__name__,
            }
