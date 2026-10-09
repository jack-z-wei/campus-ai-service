from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode
from pydantic import Field

from agents import campus_customer_service as campus_agent_module
from agents import get_agent
from agents.campus_tools import CAMPUS_TOOLS
from campus.tools.status import CampusStatusTools
from core import settings


def _tool_graph(tool):
    builder = StateGraph(MessagesState)
    builder.add_node("tools", ToolNode([tool], handle_tool_errors=True))
    builder.set_entry_point("tools")
    builder.add_edge("tools", END)
    return builder.compile()


class _QueuedModel(BaseChatModel):
    responses: list[AIMessage]
    seen_messages: list[list[BaseMessage]] = Field(default_factory=list)
    seen_tool_names: list[list[str]] = Field(default_factory=list)

    @property
    def _llm_type(self) -> str:
        return "campus-test-queue"

    def bind_tools(self, tools, *, tool_choice=None, **kwargs):
        self.seen_tool_names.append([tool.name for tool in tools])
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        self.seen_messages.append(list(messages))
        response = self.responses.pop(0)
        return ChatResult(generations=[ChatGeneration(message=response)])


def test_campus_agent_is_registered_and_runtime_is_hidden_from_tool_schema() -> None:
    assert get_agent("campus-customer-service") is not None
    status_tool = next(tool for tool in CAMPUS_TOOLS if tool.name == "query_application_status")
    schema = status_tool.tool_call_schema.model_json_schema()
    assert set(schema["properties"]) == {"record_id", "service_type"}
    assert schema["required"] == ["record_id"]
    assert "runtime" not in schema["properties"]
    assert "simulation_user_id" not in schema["properties"]
    search_schema = next(
        tool for tool in CAMPUS_TOOLS if tool.name == "search_campus_knowledge"
    ).tool_call_schema.model_json_schema()
    assert set(search_schema["properties"]) == {"query"}


@pytest.mark.asyncio
async def test_registered_agent_runs_model_tool_loop_with_injected_identity(tmp_path) -> None:
    model_name = next(iter(settings.AVAILABLE_MODELS))
    model = _QueuedModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "query_application_status",
                        "args": {
                            "record_id": "SIM-REC-001",
                            "service_type": "aid_application",
                        },
                        "id": "agent-test-status-call",
                        "type": "tool_call",
                    }
                ],
            ),
            AIMessage(content="模拟记录显示：材料审核中。"),
        ]
    )
    status_service = CampusStatusTools(tmp_path / "agent-loop.sqlite3")
    with (
        patch.object(campus_agent_module, "get_model", return_value=model),
        patch("agents.campus_tools.get_campus_status_tools", return_value=status_service),
    ):
        result = await campus_agent_module.campus_customer_service.ainvoke(
            {"messages": [{"role": "user", "content": "查一下 SIM-REC-001"}]},
            config={
                "configurable": {
                    "thread_id": "campus-agent-unit-test",
                    "model": model_name,
                    "simulation_user_id": "SIM-USER-001",
                },
                "recursion_limit": 8,
            },
        )

    messages = result["messages"]
    assert len(messages) == 4
    assert isinstance(messages[2], ToolMessage)
    assert json.loads(messages[2].content)["status"] == "材料审核中"
    assert messages[-1].content == "模拟记录显示：材料审核中。"


@pytest.mark.asyncio
async def test_agent_hides_business_tools_and_blocks_them_without_demo_identity() -> None:
    model_name = next(iter(settings.AVAILABLE_MODELS))
    model = _QueuedModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "query_application_status",
                        "args": {"record_id": "SIM-REC-001"},
                        "id": "unconfigured-identity-call",
                        "type": "tool_call",
                    }
                ],
            )
        ]
    )
    with patch.object(campus_agent_module, "get_model", return_value=model):
        result = await campus_agent_module.campus_customer_service.ainvoke(
            {"messages": [{"role": "user", "content": "帮我查 SIM-REC-001。"}]},
            config={"configurable": {"thread_id": "no-demo-identity", "model": model_name}},
        )

    assert model.seen_tool_names == [["search_campus_knowledge"]]
    assert isinstance(result["messages"][-1], AIMessage)
    assert not result["messages"][-1].tool_calls
    assert "身份配置" in result["messages"][-1].content


@pytest.mark.asyncio
async def test_tool_runtime_injects_selected_synthetic_identity(tmp_path) -> None:
    status_tool = next(tool for tool in CAMPUS_TOOLS if tool.name == "query_application_status")
    graph = _tool_graph(status_tool)
    service = CampusStatusTools(tmp_path / "campus.sqlite3")
    call = {
        "name": "query_application_status",
        "args": {"record_id": "SIM-REC-001", "service_type": "aid_application"},
        "id": "status-call-001",
        "type": "tool_call",
    }

    with patch("agents.campus_tools.get_campus_status_tools", return_value=service):
        result = await graph.ainvoke(
            {"messages": [AIMessage(content="", tool_calls=[call])]},
            config={"configurable": {"simulation_user_id": "SIM-USER-001"}},
        )

    message = result["messages"][-1]
    assert isinstance(message, ToolMessage)
    payload = json.loads(message.content)
    assert payload["outcome"] == "found"
    assert payload["status"] == "材料审核中"
    assert payload["simulation_only"] is True


@pytest.mark.asyncio
async def test_tool_runtime_cannot_read_another_synthetic_users_record(tmp_path) -> None:
    status_tool = next(tool for tool in CAMPUS_TOOLS if tool.name == "query_application_status")
    graph = _tool_graph(status_tool)
    service = CampusStatusTools(tmp_path / "campus.sqlite3")
    call = {
        "name": "query_application_status",
        "args": {"record_id": "SIM-REC-002", "service_type": "dorm_repair"},
        "id": "status-call-002",
        "type": "tool_call",
    }

    with patch("agents.campus_tools.get_campus_status_tools", return_value=service):
        result = await graph.ainvoke(
            {"messages": [AIMessage(content="", tool_calls=[call])]},
            config={"configurable": {"simulation_user_id": "SIM-USER-001"}},
        )

    payload = json.loads(result["messages"][-1].content)
    assert payload["outcome"] == "forbidden"
    assert "SIM-USER-002" not in json.dumps(payload, ensure_ascii=False)


@pytest.mark.asyncio
async def test_checkpoint_thread_does_not_reuse_messages_after_demo_identity_switch(
    tmp_path,
) -> None:
    model_name = next(iter(settings.AVAILABLE_MODELS))
    model = _QueuedModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "query_application_status",
                        "args": {
                            "record_id": "SIM-REC-001",
                            "service_type": "aid_application",
                        },
                        "id": "identity-switch-status-call",
                        "type": "tool_call",
                    }
                ],
            ),
            AIMessage(content="该模拟申请目前处于材料审核中。"),
            AIMessage(content="当前模拟身份下无法访问之前对话的业务记录。"),
        ]
    )
    status_service = CampusStatusTools(tmp_path / "identity-switch.sqlite3")
    graph = campus_agent_module.campus_customer_service
    original_checkpointer = graph.checkpointer
    try:
        async with AsyncSqliteSaver.from_conn_string(
            str(tmp_path / "identity-switch-checkpoints.db")
        ) as saver:
            await saver.setup()
            graph.checkpointer = saver
            with (
                patch.object(campus_agent_module, "get_model", return_value=model),
                patch("agents.campus_tools.get_campus_status_tools", return_value=status_service),
            ):
                common = {
                    "thread_id": "same-browser-thread",
                    "user_id": "same-browser-user",
                    "model": model_name,
                }
                await graph.ainvoke(
                    {"messages": [{"role": "user", "content": "查 SIM-REC-001 的状态。"}]},
                    config={"configurable": {**common, "simulation_user_id": "SIM-USER-001"}},
                )
                await graph.ainvoke(
                    {"messages": [{"role": "user", "content": "那刚才的记录现在如何？"}]},
                    config={"configurable": {**common, "simulation_user_id": "SIM-USER-002"}},
                )
    finally:
        graph.checkpointer = original_checkpointer

    second_turn_model_input = "\n".join(str(message.content) for message in model.seen_messages[-1])
    assert "材料审核中" not in second_turn_model_input
