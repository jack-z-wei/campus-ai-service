"""Campus-specific LangGraph agent adapted from the upstream RAG agent pattern."""

from typing import Literal

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    RemoveMessage,
    SystemMessage,
)
from langchain_core.runnables import RunnableConfig, RunnableLambda, RunnableSerializable
from langgraph.graph import END, MessagesState, StateGraph
from langgraph.managed import RemainingSteps
from langgraph.prebuilt import ToolNode

from agents.campus_tools import CAMPUS_TOOLS, tools_for_simulation_identity
from core import get_model, settings
from schema.models import DeepseekModelName


class CampusAgentState(MessagesState, total=False):
    remaining_steps: RemainingSteps
    campus_simulation_user_id: str | None


PROMPT_PATH = "prompts/campus_system_v1.md"
MAX_TOOL_CALLS_PER_MODEL_TURN = 2
MAX_OUTPUT_TOKENS_PER_MODEL_TURN = 768
MAX_MEMORY_TURNS = 4


def _system_prompt() -> str:
    from pathlib import Path

    return (Path(__file__).resolve().parents[2] / PROMPT_PATH).read_text(encoding="utf-8")


def recent_messages_for_model(
    messages: list[BaseMessage], *, max_turns: int = MAX_MEMORY_TURNS
) -> list[BaseMessage]:
    """Bound the model context to the most recent complete user turns.

    The checkpointer still keeps its full transcript for the history panel. This window
    controls what is sent to the model, preventing old turns from growing the prompt.
    """
    if max_turns < 1:
        raise ValueError("max_turns must be positive.")
    user_turn_starts = [
        index for index, message in enumerate(messages) if isinstance(message, HumanMessage)
    ]
    if len(user_turn_starts) <= max_turns:
        return messages
    return messages[user_turn_starts[-max_turns] :]


def wrap_model(
    model: BaseChatModel,
    model_name: object,
    *,
    simulation_user_id: object = None,
) -> RunnableSerializable:
    available_tools = tools_for_simulation_identity(simulation_user_id)
    bound_model = model.bind_tools(available_tools, tool_choice="auto")
    if isinstance(model_name, DeepseekModelName):
        bound_model = bound_model.bind(
            max_tokens=MAX_OUTPUT_TOKENS_PER_MODEL_TURN,
            extra_body={"thinking": {"type": "disabled"}},
        )
    else:
        bound_model = bound_model.bind(max_tokens=MAX_OUTPUT_TOKENS_PER_MODEL_TURN)
    system_messages = [SystemMessage(content=_system_prompt())]
    if len(available_tools) != len(CAMPUS_TOOLS):
        system_messages.append(
            SystemMessage(
                content=(
                    "本次服务端没有配置有效的课程演示身份。用户询问个人状态或要求创建"
                    "模拟工单时，禁止调用任何工具，直接提示先完成身份配置；公开校园信息"
                    "问题仍可使用知识检索工具。"
                )
            )
        )
    preprocessor = RunnableLambda(
        lambda state: system_messages + recent_messages_for_model(state["messages"]),
        name="CampusPrompt",
    )
    return preprocessor | bound_model


def scope_messages_to_simulation_identity(
    state: CampusAgentState, config: RunnableConfig
) -> CampusAgentState:
    """Drop prior turns when a checkpoint is used with another demo identity.

    The UI allows changing the selected identity while keeping the same thread. The
    tool runtime rechecks ownership, but old tool results in checkpointed messages
    would otherwise remain visible to the next identity.
    """
    configurable = config.get("configurable", {})
    current_identity = configurable.get("simulation_user_id")
    if (
        "campus_simulation_user_id" in state
        and state["campus_simulation_user_id"] == current_identity
    ):
        return {}

    messages = state.get("messages", [])
    latest_user_message = next(
        (message for message in reversed(messages) if isinstance(message, HumanMessage)),
        None,
    )
    remove_messages = [
        RemoveMessage(id=message.id)
        for message in messages
        if message.id is not None and message is not latest_user_message
    ]
    return {
        "messages": remove_messages,
        "campus_simulation_user_id": current_identity,
    }


async def call_model(state: CampusAgentState, config: RunnableConfig) -> CampusAgentState:
    requested = config.get("configurable", {}).get("model", settings.DEFAULT_MODEL)
    if requested is None:
        requested = DeepseekModelName.DEEPSEEK_FLASH
    if isinstance(requested, str):
        requested = next(
            (available for available in settings.AVAILABLE_MODELS if available.value == requested),
            None,
        )
    if requested not in settings.AVAILABLE_MODELS:
        raise ValueError("The requested model is not available to the campus agent.")
    model = get_model(requested)
    simulation_user_id = config.get("configurable", {}).get("simulation_user_id")
    response = await wrap_model(model, requested, simulation_user_id=simulation_user_id).ainvoke(
        state, config
    )

    allowed_tool_names = {tool.name for tool in tools_for_simulation_identity(simulation_user_id)}
    if any(tool_call.get("name") not in allowed_tool_names for tool_call in response.tool_calls):
        response = AIMessage(content="请先完成演示身份配置，再查询模拟记录或创建模拟工单。")

    remaining_steps = state.get("remaining_steps", 25)
    if remaining_steps < 2 and response.tool_calls:
        response = AIMessage(
            id=response.id,
            content="本轮工具调用次数已达到上限，当前无法安全完成请求。",
        )
    elif len(response.tool_calls) > MAX_TOOL_CALLS_PER_MODEL_TURN:
        response = AIMessage(
            id=response.id,
            content="一次请求需要的工具数量超过安全上限，请缩小问题范围后重试。",
        )
    return {"messages": [response]}


def route_after_model(state: CampusAgentState) -> Literal["tools", "done"]:
    last_message = state["messages"][-1]
    if not isinstance(last_message, AIMessage):
        raise TypeError(f"Expected AIMessage, received {type(last_message).__name__}.")
    return "tools" if last_message.tool_calls else "done"


builder = StateGraph(CampusAgentState)
builder.add_node("identity_scope", scope_messages_to_simulation_identity)
builder.add_node("model", call_model)
builder.add_node("tools", ToolNode(CAMPUS_TOOLS, handle_tool_errors=True))
builder.set_entry_point("identity_scope")
builder.add_edge("identity_scope", "model")
builder.add_edge("tools", "model")
builder.add_conditional_edges(
    "model",
    route_after_model,
    {"tools": "tools", "done": END},
)
campus_customer_service = builder.compile()
