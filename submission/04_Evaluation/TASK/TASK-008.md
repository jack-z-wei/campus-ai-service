# TASK-008：会话记忆、隔离与清空

- 状态：已完成（双路线多轮、清空、隔离、有界上下文和本地模拟转人工均已在 Windows 实测；全量 21 题仍归 TASK-010）
- 目标：按课程计划完成两条 Python 路线的有界上下文、跨轮续聊、身份/会话隔离和清空；保存真实多轮 trace。
- 修改范围：原理版 SQLite 会话记忆与 CLI；上游工程版 SQLite checkpoint 删除入口、模型上下文窗口和 Streamlit 控件；相应测试与进度报告。
- 验收条件：
  1. 原理版每个 session 按合成身份隔离，最多存最近 4 轮成功问答；失败回答不落库；支持明示 session ID 清空。
  2. 工程版继续使用上游 SQLite checkpointer，并把最近 4 个用户轮次交给模型；服务端删除前确认 checkpoint 元数据中的 `user_id` 与 `agent_id`。
  3. 使用临时 SQLite 实测记忆的裁剪、隔离、清空，以及真实 checkpointer 的跨用户拒绝删除。
  4. M01/M02 顺序逐轮真实调用；模型使用实际多轮历史；M02 第二轮必须执行本地模拟转人工工具，留下工单 ID 与原始 trace；失败如实保存。
  5. 更新本任务、Agent Baseline、失败分析和总进度；不修改冻结 gold。
- 本地事实：上游固定版本已通过 `src/service/service.py` 启动时为 Agent 附加 SQLite saver；已检查安装的 `AsyncSqliteSaver.adelete_thread(thread_id)`，可清 checkpoint 与 writes。上游模板线程 API 原先只有列表/历史；Streamlit “New Chat”只是新建 thread，不删除旧存储。
- 原理版策略：用 SQLite 保存成功的 user/assistant 完整轮次，服务运行期发送最近 4 轮给直接 HTTPX Function Calling Agent；不在 history 中重放工具内部消息；session 行绑定 synthetic user ID。数据库放在被忽略的 `runs/principles_memory.sqlite3`。
- 工程版策略：保留上游全量 checkpoint transcript 供历史界面显示；发给 Campus Agent 模型的消息仅取最近 4 个 HumanMessage 开始的完整轮次。这个边界控制模型上下文长度；历史数据库物理清除通过显式的线程删除动作。
- 已修改：`src/campus/conversation_memory.py`、`src/campus/principle_agent.py`、`scripts/run_campus_principles_windows.py`、`scripts/run_campus_principles_multiturn_windows.py`、`scripts/clear_principle_memory_windows.py`、`src/agents/campus_customer_service.py`、`src/service/service.py`、`src/client/client.py`、`src/streamlit_app.py` 及定向测试。
- Windows 定向测试先发现两处测试夹具问题（LangChain 不允许 `AIMessage(content=None)`；跨 Agent 测试实际请求了正确归属 Agent），修正夹具后相关套件最终为 `46 passed, 6 warnings`。Ruff 与修改文件 `py_compile` 均通过；另有真实 SQLite checkpoint API 集成验证。
- 原理版 M01：`runs/principles-multiturn-20261006-184014-e3debe8c/`。两轮均完成，第一轮追问且 0 工具调用，第二轮发送前轮历史并使用正确参数调用状态 Tool；记忆轮数从 0 到 1。3 次模型响应，输入 9,175、输出 200 tokens，估算 US$0.0029925。
- 原理版 M02：`runs/principles-multiturn-20261006-184055-dedf150d/`。第一轮状态 Tool 命中 SIM-REC-002，第二轮跨轮引用并调用模拟工单 Tool；回传 ticket `SIM-TICKET-ce1b980498875ed2`，数据库有 requester/type/record/reason/status，且 `real_human_contacted=false`。4 次模型响应，输入 13,895、输出 399 tokens，估算 US$0.0046473。
- 工程版 M01：`runs/engineering-multiturn-20261006-184452-62342997/`。复用上游 `AsyncSqliteSaver` thread，第一轮追问，第二轮跨轮查状态；限制模型上下文最近 4 轮，thread 元数据可按上游 `adelete_thread` 清理；保留 trace、删除隔离测试 thread。3 次模型响应，输入 2,964、输出 186 tokens，估算 US$0.0011124。
- 工程版 M02：`runs/engineering-multiturn-20261006-184518-5069f94b/`。两轮 checkpoint 连续，第二轮创建 `SIM-TICKET-09fca15ada3e5a55`，结果标记只写本地合成数据。4 次模型响应，输入 4,687、输出 455 tokens，估算 US$0.0019521；实验结束后按 thread ID 删除 checkpoint。
- SQLite 记忆单元测试覆盖最近 3 轮裁剪、session/user 隔离、跨身份读写拒绝与清空；工程删除 API 的临时数据库测试覆盖 user/agent 元数据过滤，`tests/service/test_threads_sqlite.py` 用真实 `AsyncSqliteSaver` 验证本人删除成功及跨用户删除 404 且对方 thread 仍存在。
- Windows 原理版清空命令另外在隔离 SQLite 文件上执行：`clear_principle_memory_windows.py` 返回 `cleared`，随后 history 为空；记录为 `runs/principle-memory-clear-cli-smoke-20261006/manifest.json`，未调用聊天 API。
- 本任务真实模型共新增 14 次响应，输入 30,721、输出 1,240 tokens，峰时全输入未命中缓存估算 US$0.0107043。Coze 调用 0；不含平台费用。账号实际账单未知。
- 本次新增实验未观察到多轮、Tool Call 或转人工失效；此前 K01 上下文截断、原 S01 工具追问和首次失败轨迹均未覆盖或删除。S01 gold 参数差异、完整固定集评测、人工评分和 UI 可视 Trace 仍单独保留待办。
- 用户参与：无需写代码。若后续工程环境内演示清空，UI 明确标注为永久删除且需要点击二次确认式按钮；API 依赖现有 Bearer 密钥。原理版 CLI 清空命令使用 `--session-id` 和所属合成身份。
- 证据：`tests/campus/test_conversation_memory.py`、`tests/campus/test_campus_customer_service_memory.py`、`tests/campus/test_principle_agent.py`、`tests/service/test_threads.py`、`tests/service/test_threads_sqlite.py`、`tests/client/test_client.py`；后续真实运行留在 `runs/principles-multiturn-*`。
