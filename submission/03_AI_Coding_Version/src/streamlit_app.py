import asyncio
import os
import uuid
from collections.abc import AsyncGenerator
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from pydantic import ValidationError

from client import AgentClient, AgentClientError
from schema import ChatHistory, ChatMessage, UserThreads
from schema.task_data import TaskData, TaskDataStatus

# 长安大学校园智能客服助手的 Streamlit 前端。
# 页面通过 AgentClient 连接本地 FastAPI 服务，处理校园知识问答与演示业务查询。

# - main() - sets up the streamlit app and high level structure
# - draw_messages() - draws a set of chat messages - either replaying existing messages
#   or streaming new ones.
# The app heavily uses AgentClient to interact with the agent's FastAPI endpoints.


APP_TITLE = "长安大学校园智能客服助手"
APP_ICON = "🎓"
CAMPUS_AGENT = "campus-customer-service"
USER_ID_COOKIE = "user_id"


def campus_tool_label(name: str) -> tuple[str, str]:
    """Return a student-facing label and completion note for a campus tool."""
    labels = {
        "search_campus_knowledge": ("🔎 正在查找校园公开资料", "已完成资料检索"),
        "query_application_status": ("🧾 正在核对模拟事项记录", "已完成模拟记录核对"),
        "create_human_service_request": ("🧑‍💼 正在登记模拟人工服务", "已登记模拟服务事项"),
    }
    if name in labels:
        return labels[name]
    if "transfer_to" in name:
        return "🤝 正在协同处理咨询", "已完成协同处理"
    return "💬 正在处理校园咨询", "已完成咨询处理"


def get_or_create_user_id() -> str:
    """Get the user ID from session state or URL parameters, or create a new one if it doesn't exist."""
    # Check if user_id exists in session state
    if USER_ID_COOKIE in st.session_state:
        return st.session_state[USER_ID_COOKIE]

    # Try to get from URL parameters using the new st.query_params
    if USER_ID_COOKIE in st.query_params:
        user_id = st.query_params[USER_ID_COOKIE]
        st.session_state[USER_ID_COOKIE] = user_id
        return user_id

    # Generate a new user_id if not found
    user_id = str(uuid.uuid4())

    # Store in session state for this session
    st.session_state[USER_ID_COOKIE] = user_id

    # Also add to URL parameters so it can be bookmarked/shared
    st.query_params[USER_ID_COOKIE] = user_id

    return user_id


@st.cache_data(ttl=600, show_spinner=False)
def fetch_user_threads_cached(
    base_url: str, user_id: str, agent_id: str | None = None, limit: int = 20
) -> UserThreads:
    """
    Fetch and cache user threads using the new synchronous get_user_threads method.
    """
    client = AgentClient(base_url=base_url, get_info=False)
    return client.get_user_threads(user_id=user_id, agent=agent_id, limit=limit)


async def main() -> None:
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon=APP_ICON,
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={},
    )

    # Hide the streamlit upper-right chrome
    st.html(
        """
        <style>
        :root {
            --campus-ink: #17324d;
            --campus-teal: #0b7a75;
            --campus-mist: #edf5f4;
        }
        .stApp { background: linear-gradient(180deg, #f7fafc 0%, #ffffff 42%); }
        [data-testid="stSidebar"] { background: #f1f6f7; }
        [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3 { color: var(--campus-ink); }
        [data-testid="stSidebar"] h2 { font-size: 1.3rem; line-height: 1.35; }
        [data-testid="stChatMessage"] { border-radius: 16px; max-width: 1040px; margin-left: auto; margin-right: auto; }
        [data-testid="stChatInput"] { border-color: #c9d9df; }
        .campus-eyebrow { color: var(--campus-teal); font-size: .83rem; font-weight: 700; letter-spacing: .08em; }
        .campus-title { color: var(--campus-ink); font-size: 2rem; font-weight: 750; margin: .25rem 0; }
        .campus-sidebar-title { color: var(--campus-ink); font-size: 1.05rem; font-weight: 750; line-height: 1.35; white-space: nowrap; margin: .25rem 0 .8rem 0; }
        .campus-subtitle { color: #526777; margin: 0 0 1rem 0; }
        .campus-card { background: white; border: 1px solid #dce7ea; border-radius: 14px; padding: 1rem 1.1rem; height: 100%; max-width: 1040px; }
        .campus-card strong { color: var(--campus-ink); }
        .campus-note { color: #526777; background: var(--campus-mist); border-left: 4px solid var(--campus-teal); border-radius: 8px; padding: .7rem .9rem; }
        [data-testid="stStatusWidget"] {
                visibility: hidden;
                height: 0%;
                position: fixed;
            }
        </style>
        """,
    )
    if st.get_option("client.toolbarMode") != "minimal":
        st.set_option("client.toolbarMode", "minimal")
        await asyncio.sleep(0.1)
        st.rerun()

    # Get or create user ID
    user_id = get_or_create_user_id()

    if "agent_client" not in st.session_state:
        load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")
        agent_url = os.getenv("AGENT_URL")
        if not agent_url:
            host = os.getenv("HOST", "0.0.0.0")
            port = os.getenv("PORT", 8080)
            agent_url = f"http://{host}:{port}"
        try:
            with st.spinner("Connecting to agent service..."):
                st.session_state.agent_client = AgentClient(base_url=agent_url)
        except AgentClientError as e:
            st.error(f"Error connecting to agent service at {agent_url}: {e}")
            st.markdown("The service might be booting up. Try again in a few seconds.")
            st.stop()
    agent_client: AgentClient = st.session_state.agent_client

    available_agents = [agent.key for agent in agent_client.info.agents]
    if CAMPUS_AGENT not in available_agents:
        st.error("当前服务没有启用校园客服，请先启动校园客服 API 配置。")
        st.stop()
    # This is a single-purpose campus assistant; the selected graph is not user-switchable.
    agent_client.agent = CAMPUS_AGENT

    if "thread_id" not in st.session_state:
        thread_id = st.query_params.get("thread_id")
        if not thread_id:
            thread_id = str(uuid.uuid4())
            messages = []
        else:
            try:
                messages: ChatHistory = agent_client.get_history(
                    thread_id=thread_id, agent=CAMPUS_AGENT
                ).messages
            except AgentClientError:
                st.error("No message history found for this Thread ID.")
                messages = []
        st.session_state.messages = messages
        st.session_state.thread_id = thread_id

    # Keep thread_id in the URL so the address bar is directly shareable.
    st.query_params["thread_id"] = st.session_state.thread_id
    st.query_params.pop("agent", None)

    st.markdown(
        """
        <div class="campus-eyebrow">长安大学 · 校园服务｜课程演示版</div>
        <div class="campus-title">长安大学校园智能客服助手</div>
        <div class="campus-subtitle">校园政策问答、办事状态查询与人工服务登记</div>
        """,
        unsafe_allow_html=True,
    )

    # Config options
    with st.sidebar:
        st.markdown(
            f'<div class="campus-sidebar-title">{APP_ICON} {APP_TITLE}</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="campus-note">面向校园常见咨询的课程演示系统。政策回答附资料来源；业务状态与服务登记使用合成数据。</div>',
            unsafe_allow_html=True,
        )

        if st.button(":material/chat: 开始新咨询", use_container_width=True):
            st.session_state.messages = []
            st.session_state.thread_id = str(uuid.uuid4())
            st.rerun()

        with st.popover(":material/delete: 删除本次咨询记录", use_container_width=True):
            st.warning("确认后会删除本次对话的已保存记录，此操作不可撤销。")
            if st.button("确认删除", type="primary", key="delete_current_thread"):
                try:
                    agent_client.delete_thread(
                        st.session_state.thread_id,
                        user_id=user_id,
                        agent=CAMPUS_AGENT,
                    )
                except AgentClientError as error:
                    st.error(str(error))
                else:
                    st.session_state.messages = []
                    st.session_state.thread_id = str(uuid.uuid4())
                    st.query_params["thread_id"] = st.session_state.thread_id
                    st.query_params.pop("agent", None)
                    fetch_user_threads_cached.clear()
                    st.rerun()

        with st.expander(":material/history: 最近的咨询", expanded=False):
            try:
                user_threads = fetch_user_threads_cached(
                    base_url=agent_client.base_url,
                    user_id=user_id,
                    agent_id=CAMPUS_AGENT,
                    limit=20,
                )
                thread_list = user_threads.threads
            except Exception as e:
                st.caption(f"暂时无法读取咨询记录：{e}")
                thread_list = []

            for t in thread_list:
                label = t.title or f"Chat {t.thread_id[:8]}"
                if st.button(label, key=f"thread_{t.thread_id}", use_container_width=True):
                    try:
                        history: ChatHistory = agent_client.get_history(
                            thread_id=t.thread_id, agent=CAMPUS_AGENT
                        )
                    except AgentClientError:
                        st.error("暂时无法打开这条咨询记录。")
                        continue
                    st.session_state.messages = history.messages
                    st.session_state.thread_id = t.thread_id
                    st.query_params["thread_id"] = t.thread_id
                    st.rerun()

        with st.popover(":material/tune: 演示设置", use_container_width=True):
            model_idx = agent_client.info.models.index(agent_client.info.default_model)
            model = st.selectbox("回答模型", options=agent_client.info.models, index=model_idx)
            st.caption("仅用于本次课程演示；更换模型不会改变已有对话记录。")
            simulation_user_id = st.selectbox(
                "合成演示身份（非真实账号）",
                options=["SIM-USER-001", "SIM-USER-002", "SIM-USER-003"],
                format_func=lambda value: {
                    "SIM-USER-001": "演示用户 001 · 助学申请",
                    "SIM-USER-002": "演示用户 002 · 宿舍维修",
                    "SIM-USER-003": "演示用户 003 · 图书馆服务",
                }[value],
                key="campus_simulation_user_id",
            )
            use_streaming = st.toggle("逐字显示回答", value=True)

        @st.dialog("服务范围与数据说明")
        def service_scope_dialog() -> None:
            st.markdown("""
            本助手用于长安大学校园服务场景课程演示，当前提供：

            - **校园知识问答**：检索已整理的学校公开资料，并在回答中展示来源。
            - **办事状态查询**：仅查询课程内的合成演示记录。
            - **人工服务登记**：仅创建本地演示工单，不会通知真实工作人员。

            请勿输入真实姓名、学号、联系方式或其他个人信息。政策文件的版本与时效请以学校最新正式通知为准。
            """)

        if st.button(":material/info: 服务说明", use_container_width=True):
            service_scope_dialog()
        st.caption("课程演示版 · 资料来源以回答中列出的官方页面为准")

    # Draw existing messages
    messages: list[ChatMessage] = st.session_state.messages

    if len(messages) == 0:
        with st.chat_message("ai", avatar=APP_ICON):
            st.write("你好！可以咨询校园政策与图书馆服务，也可查询模拟办事记录。")
            st.markdown(
                """
                <div class="campus-card">
                  <strong>你可以这样问</strong><br>
                  · 本科生每学期修读多少学分比较合适？<br>
                  · 图书馆公开的联系电话和邮箱是什么？<br>
                  · 我的模拟申请进度如何？<br><br>
                  <span style="color:#526777">状态查询与服务登记使用合成数据；回答附可核验来源。</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # draw_messages() expects an async iterator over messages
    async def amessage_iter() -> AsyncGenerator[ChatMessage, None]:
        for m in messages:
            yield m

    await draw_messages(amessage_iter())

    user_input = st.chat_input("输入校园问题或模拟办事需求…")

    if user_input:
        messages.append(ChatMessage(type="human", content=user_input))
        st.chat_message("human").write(user_input)
        try:
            agent_kwargs = {
                "message": user_input,
                "model": model,
                "thread_id": st.session_state.thread_id,
                "user_id": user_id,
            }
            agent_kwargs["agent_config"] = {"simulation_user_id": simulation_user_id}
            if use_streaming:
                stream = agent_client.astream(**agent_kwargs)
                await draw_messages(stream, is_new=True)
            else:
                response = await agent_client.ainvoke(**agent_kwargs)
                messages.append(response)
                with st.chat_message("ai", avatar=APP_ICON):
                    st.write(response.content)
            fetch_user_threads_cached.clear()
            st.rerun()  # Clear stale containers
        except AgentClientError as e:
            st.error(f"Error generating response: {e}")
            st.stop()

async def draw_messages(
    messages_agen: AsyncGenerator[ChatMessage | str, None],
    is_new: bool = False,
) -> None:
    """
    Draws a set of chat messages - either replaying existing messages
    or streaming new ones.

    This function has additional logic to handle streaming tokens and tool calls.
    - Use a placeholder container to render streaming tokens as they arrive.
    - Use a status container to render tool calls. Track the tool inputs and outputs
      and update the status container accordingly.

    The function also needs to track the last message container in session state
    since later messages can draw to the same container. This is also used for
    drawing the feedback widget in the latest chat message.

    Args:
        messages_aiter: An async iterator over messages to draw.
        is_new: Whether the messages are new or not.
    """

    # Keep track of the last message container
    last_message_type = None
    st.session_state.last_message = None

    # Placeholder for intermediate streaming tokens
    streaming_content = ""
    streaming_placeholder = None

    # Iterate over the messages and draw them
    while msg := await anext(messages_agen, None):
        # str message represents an intermediate token being streamed
        if isinstance(msg, str):
            # If placeholder is empty, this is the first token of a new message
            # being streamed. We need to do setup.
            if not streaming_placeholder:
                if last_message_type != "ai":
                    last_message_type = "ai"
                    st.session_state.last_message = st.chat_message("ai", avatar=APP_ICON)
                with st.session_state.last_message:
                    streaming_placeholder = st.empty()

            streaming_content += msg
            streaming_placeholder.write(streaming_content)
            continue
        if not isinstance(msg, ChatMessage):
            st.error(f"Unexpected message type: {type(msg)}")
            st.write(msg)
            st.stop()

        match msg.type:
            # A message from the user, the easiest case
            case "human":
                last_message_type = "human"
                st.chat_message("human").write(msg.content)

            # A message from the agent is the most complex case, since we need to
            # handle streaming tokens and tool calls.
            case "ai":
                # If we're rendering new messages, store the message in session state
                if is_new:
                    st.session_state.messages.append(msg)

                # If the last message type was not AI, create a new chat message
                if last_message_type != "ai":
                    last_message_type = "ai"
                    st.session_state.last_message = st.chat_message("ai", avatar=APP_ICON)

                with st.session_state.last_message:
                    # If the message has content, write it out.
                    # Reset the streaming variables to prepare for the next message.
                    campus_tool_names = {
                        "search_campus_knowledge",
                        "query_application_status",
                        "create_human_service_request",
                    }
                    has_campus_tool_call = any(
                        call.get("name") in campus_tool_names for call in msg.tool_calls
                    )
                    if msg.content and not has_campus_tool_call:
                        if streaming_placeholder:
                            streaming_placeholder.write(msg.content)
                            streaming_content = ""
                            streaming_placeholder = None
                        else:
                            st.write(msg.content)

                    if msg.tool_calls:
                        # Create a status container for each tool call and store the
                        # status container by ID to ensure results are mapped to the
                        # correct status container.
                        call_results = {}
                        for tool_call in msg.tool_calls:
                            label, _ = campus_tool_label(tool_call["name"])

                            status = st.status(
                                label,
                                state="running" if is_new else "complete",
                            )
                            call_results[tool_call["id"]] = status

                        # Expect one ToolMessage for each tool call.
                        for tool_call in msg.tool_calls:
                            if "transfer_to" in tool_call["name"]:
                                status = call_results[tool_call["id"]]
                                status.update(expanded=True)
                                await handle_sub_agent_msgs(messages_agen, status, is_new)
                                break

                            # Only non-transfer tool calls reach this point
                            status = call_results[tool_call["id"]]
                            tool_result: ChatMessage = await anext(messages_agen)

                            if tool_result.type != "tool":
                                st.error(f"Unexpected ChatMessage type: {tool_result.type}")
                                st.write(tool_result)
                                st.stop()

                            # Record the message if it's new, and update the correct
                            # status container with the result
                            if is_new:
                                st.session_state.messages.append(tool_result)
                            if tool_result.tool_call_id:
                                status = call_results[tool_result.tool_call_id]
                            _, completion_note = campus_tool_label(tool_call["name"])
                            status.write(completion_note)
                            status.update(state="complete")

            case "custom":
                # CustomData example used by the bg-task-agent
                # See:
                # - src/agents/utils.py CustomData
                # - src/agents/bg_task_agent/task.py
                try:
                    task_data: TaskData = TaskData.model_validate(msg.custom_data)
                except ValidationError:
                    st.error("Unexpected CustomData message received from agent")
                    st.write(msg.custom_data)
                    st.stop()

                if is_new:
                    st.session_state.messages.append(msg)

                if last_message_type != "task":
                    last_message_type = "task"
                    st.session_state.last_message = st.chat_message(
                        name="task", avatar=":material/manufacturing:"
                    )
                    with st.session_state.last_message:
                        status = TaskDataStatus()

                status.add_and_draw_task_data(task_data)

            # In case of an unexpected message type, log an error and stop
            case _:
                st.error(f"Unexpected ChatMessage type: {msg.type}")
                st.write(msg)
                st.stop()


async def handle_sub_agent_msgs(messages_agen, status, is_new):
    """
    This function segregates agent output into a status container.
    It handles all messages after the initial tool call message
    until it reaches the final AI message.

    Enhanced to support nested multi-agent hierarchies with handoff back messages.

    Args:
        messages_agen: Async generator of messages
        status: the status container for the current agent
        is_new: Whether messages are new or replayed
    """
    nested_popovers = {}

    # looking for the transfer Success tool call message
    first_msg = await anext(messages_agen)
    if is_new:
        st.session_state.messages.append(first_msg)

    # Continue reading until we get an explicit handoff back
    while True:
        # Read next message
        sub_msg = await anext(messages_agen)

        # this should only happen is skip_stream flag is removed
        # if isinstance(sub_msg, str):
        #     continue

        if is_new:
            st.session_state.messages.append(sub_msg)

        # Handle tool results with nested popovers
        if sub_msg.type == "tool" and sub_msg.tool_call_id in nested_popovers:
            popover = nested_popovers[sub_msg.tool_call_id]
            popover.write("处理完成。")
            continue

        # Handle transfer_back_to tool calls - these indicate a sub-agent is returning control
        if (
            hasattr(sub_msg, "tool_calls")
            and sub_msg.tool_calls
            and any("transfer_back_to" in tc.get("name", "") for tc in sub_msg.tool_calls)
        ):
            # Process transfer_back_to tool calls
            for tc in sub_msg.tool_calls:
                if "transfer_back_to" in tc.get("name", ""):
                    # Read the corresponding tool result
                    transfer_result = await anext(messages_agen)
                    if is_new:
                        st.session_state.messages.append(transfer_result)

            # After processing transfer back, we're done with this agent
            if status:
                status.update(state="complete")
            break

        # Display content and tool calls in the same nested status
        if status:
            if sub_msg.content:
                status.write(sub_msg.content)

            if hasattr(sub_msg, "tool_calls") and sub_msg.tool_calls:
                for tc in sub_msg.tool_calls:
                    # Check if this is a nested transfer/delegate
                    if "transfer_to" in tc["name"]:
                        # Create a nested status container for the sub-agent
                        nested_status = status.status(
                            campus_tool_label(tc["name"])[0],
                            state="running" if is_new else "complete",
                            expanded=True,
                        )

                        # Recursively handle sub-agents of this sub-agent
                        await handle_sub_agent_msgs(messages_agen, nested_status, is_new)
                    else:
                        # Regular tool call - create popover
                        label, _ = campus_tool_label(tc["name"])
                        popover = status.popover(label, icon="🔎")
                        popover.write("正在处理该校园咨询请求。")
                        # Store the popover reference using the tool call ID
                        nested_popovers[tc["id"]] = popover


if __name__ == "__main__":
    asyncio.run(main())
