# TASK-007：校园业务工具与真实 Function Calling

- 日期：2026-10-06（Asia/Shanghai）
- 状态：核心目标已完成；全 21 题及真实 API/UI Trace 展示仍在 TASK-010 和后续 UI 验收中
- 目标：实现校园业务状态查询与模拟人工请求工具，并按上游合适的 LangGraph 图模式注册校园 Agent。
- 验收：工具输入有结构约束，身份取自运行上下文、SQL 参数化、用户数据隔离；真实模型至少一次选中工具并接收结果；Agent 循环和服务调用有界；转人工只写本地合成工单。

## 复用上游方式

- 查阅固定上游 `src/agents/rag_assistant.py` 后，复用其 `StateGraph`、`ToolNode`、工具调用条件路由与 `RemainingSteps` 模式；校园图限制每轮最多两个工具调用，并在服务配置上设 `recursion_limit=10`。
- 沿用 `src/service/service.py` 启动时附加 SQLite checkpoint 的既有路径，不另写会话存储。
- 未复用上游 `database_search`：它查 AcmeTech 手册并使用 OpenAI Embeddings，与长安大学来源及本地 Ollama 不匹配。
- 上游 service 的 `user_id` 是调用方提供的对话标识，不是校园身份认证。UI 显示明确的 `SIM-USER-001/002/003` 演示身份；仅访问合成数据，不宣称真实认证。

## 实现与 Windows 验证

- `src/campus/tools/status.py` 实现合成 SQLite 状态查询和本地模拟转人工工单；身份与记录 ID 有格式验证，SQL 使用参数绑定，跨用户只返回通用权限结果，工单请求具有幂等键和本地持久化。
- `src/agents/campus_tools.py` 注册知识搜索、状态查询、模拟人工请求三个 LangChain 工具；`ToolRuntime` 和 `simulation_user_id` 不进入模型工具参数 schema。
- `src/agents/campus_customer_service.py` 实现校园 `StateGraph`；提示词要求只按返回来源回答、标清模拟数据、拒绝跨用户泄露，并避免声称真实人工已接单。
- `src/agents/agents.py` 注册 `campus-customer-service`；服务返回中的 Agent 清单已有该项。
- Streamlit 仅在选择校园 Agent 时展示“模拟演示身份（不对应真实账号）”，并将选中值通过 `agent_config` 传给服务。
- Windows `uv run pytest tests/campus -q`：Agent 工具集成版目前 `20 passed`；覆盖 3 正常/2 错误/1 未找到状态契约、工单契约、Runtime 隐藏和注入、跨用户拒绝、完整图内 fake tool-call loop。
- 真实 DeepSeek 状态工具调用：`runs/campus-agent-smoke-20261006-175330/manifest.json`；模型确实调用 `query_application_status`，实际结果与 `SIM-REC-001` 种子记录相符。两次模型调用 usage 输入 2,016、输出 174 tokens，估算 US$0.0008136；这不是实际学生状态或课程知识题评分。
- Windows fake 模式服务与 Streamlit smoke：`runs/smoke-20261006-175501/manifest.json`；校园 Agent 注册、API invoke、模拟身份选项和 UI 到服务的聊天均通过；`course_result=false`、`paid_api_request_performed=false`。
- Windows `ruff check` 和 `py_compile` 对新 Agent、服务、UI、工具测试和脚本通过。

## 尚未完成

- 固定集状态/未知/边界及全 21 题逐题基线仍待 TASK-010；不得用 M01/M02 单例代替总体结果。
- Streamlit 当前有查询历史及清空会话入口；屏幕仍未展示完整工具/RAG trace 和明确 trace_id。M01/M02 的本次真实验证经 Windows Graph+SQLite checkpoint runner 执行，未声称经过浏览器 UI。
- 状态工具的本地正常/错误/不存在契约和真实 SIM 记录均有测试；模拟业务数据不是真实校园服务连接。

## 失败测试记录

- 首次测试把 `ToolNode` 独立当作 Runnable 调用，LangGraph 因没有图内 Runtime 报 `Missing required config key`；改成单节点 `StateGraph` 后，证明运行时身份由 ToolRuntime 正确注入。
- 随后的两次断言误把输入 AIMessage 当成 ToolMessage；测试改为读取图返回的最后一条消息，工具本身无代码修改。
- 上述失败为测试调用/断言错误，已保留此过程记录；最终 Windows 测试为 20 passed。

## 当前边界

- `SIM-USER-*` 是 UI 选择的课程模拟身份，不是认证；上游 `user_id` 仍为客户端提供。安全边界只适用于本地合成演示数据库。
- 工单 ID、数据库、日期、状态均为演示数据；没有真实人工服务联系。

## 2026-10-06 原理版和工具查询策略补充

- 原理版真实 Function Calling 首次跑 S01 时，模型未选择工具并追问 `service_type`，见 `runs/principles-20261006-182527-52cdfe74/`。保留为未优化失败。
- 不要求模型根据 SIM 编号猜服务类别：`CampusStatusTools.query_application_status` 现在允许省略 `service_type`，只用已注入的 SIM 身份与用户提供的记录号查询本人唯一记录；如传入类别仍精确过滤。跨用户情形即使省略类别也仍 `forbidden`。对应回归在 `tests/campus/test_status_tools.py`。
- 原理版重跑 S01 后真实选择 `query_application_status`，只传 `SIM-REC-001`；服务端取回 `aid_application` 与“材料审核中”，模型明确标记为模拟数据。见 `runs/principles-20261006-182725-6b464d98/manifest.json` 与 `trace.json`。两次模型请求、一次工具调用；输入合计 7,260、输出 154 tokens，峰时估算 US$0.0023628。
- 冻结 S01 gold 的预期参数含 `service_type=aid_application`，本次真实调用没传该字段。因此功能结果成功，原始精确参数金标准仍记差异；不改冻结案例、不把参数指标记成满分。
- 可选字段变更后 Windows `tests/campus -q` 为 `27 passed`，Ruff 与 py_compile 通过。完整模型评测、多轮 Memory 和模拟工单真实模型工具路径继续待做。

## 2026-10-06 TASK-008 多轮与转人工实测补充

- 原理版 M01/M02 与工程版 M01/M02 均按独立 session 顺序真实运行；细节、模型 usage 和逐轮 trace 见 `TASK/TASK-008.md` 与 `reports/Agent_Baseline.md`。
- 两个 M01 都先追问，随后使用会话历史调用状态查询。两条路线的 M02 都先查到 SIM-REC-002 已派单，再在第二轮调用 `create_human_service_request`，真实写入两个不同的本地模拟 ticket；返回值都标 `created_simulated` 且未联系真人。
- memory 最近 4 轮窗口、身份隔离、清空；上游 checkpoint 的 user/agent 校验与真实 SQLite 删除均通过 46 项定向测试中的对应覆盖。此前的失败 trace 均保留。
- 以上用例完成后，工具实现目标不再因多轮或手工转接而阻塞；全固定集和完整 HTTP/UI Trace 仍未通过。
