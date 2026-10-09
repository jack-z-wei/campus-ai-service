from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from agents.campus_customer_service import MAX_MEMORY_TURNS, recent_messages_for_model


def test_engineering_agent_limits_model_context_to_recent_complete_turns() -> None:
    messages = []
    for index in range(MAX_MEMORY_TURNS + 2):
        messages.extend(
            (
                HumanMessage(content=f"question-{index}"),
                AIMessage(content="", tool_calls=[]),
                ToolMessage(content=f"tool-{index}", tool_call_id=f"call-{index}"),
                AIMessage(content=f"answer-{index}"),
            )
        )

    bounded = recent_messages_for_model(messages)

    assert len(bounded) == MAX_MEMORY_TURNS * 4
    assert bounded[0].content == f"question-{2}"
    assert bounded[-1].content == f"answer-{MAX_MEMORY_TURNS + 1}"


def test_engineering_memory_keeps_tool_cycle_inside_its_user_turn() -> None:
    messages = [
        HumanMessage(content="old"),
        AIMessage(content="old-answer"),
        HumanMessage(content="latest"),
        AIMessage(
            content="",
            tool_calls=[{"name": "query_application_status", "args": {}, "id": "call-1"}],
        ),
        ToolMessage(content="found", tool_call_id="call-1"),
    ]

    assert recent_messages_for_model(messages) == messages
