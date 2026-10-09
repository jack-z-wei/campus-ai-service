# TASK-017：Windows 运行态功能测试（FastAPI、Streamlit 与真实模型）

- 日期：2026-10-06（Asia/Shanghai）
- 状态：自动功能测试已通过；H-05 浏览器现场观感/截图仍待用户
- 依据：用户要求在 Windows 启动项目做功能测试，并明确授权实际收费模型调用。

## Docker 判断

- Windows Docker CLI 存在，Docker daemon 返回版本 `29.6.2`；`docker compose config --quiet` 成功，Compose 配置可解析。
- 本次原生 Windows 验收使用项目默认 `DATABASE_TYPE=sqlite`，不依赖 Docker。Compose 还会启动额外 Postgres 与容器版服务/UI，当前这组应用测试不需要这些服务，因此没有启动容器或创建 Docker volume。

## 无收费的实际进程与 UI/API 功能测试

- 运行 `scripts/smoke_template_windows.py`，使用 Windows 项目 `.venv` 启动真实 FastAPI 子进程和真实 Streamlit HTTP 服务，模型通过进程环境强制为 fake。
- checkpoint SQLite 路径隔离在 `runs/smoke-20261006-204949/checkpoints.sqlite3`，不复用或改写项目根目录的 `checkpoints.db`。
- FastAPI `/health` 返回 200，`/info` 返回 11 个 Agent；通用 chatbot 和校园 Agent API 均返回 fake 响应，SIM 演示参数被接受。
- Streamlit 页面 `/` 返回 200，`/_stcore/health` 与 Compose 配置使用的 `/healthz` 均返回 200；Streamlit `AppTest` 能渲染聊天框、选择 `campus-customer-service` 与 `SIM-USER-002` 并完成 fake 对话。
- 两个子进程均被脚本正常终止。整个 fake 测试 `course_result=false`，不冒充真实课程答案；没有调用收费 API。
- 完整结果、服务日志、UI 日志和隔离 SQLite 在 `runs/smoke-20261006-204949/`。

## 一条真实收费模型功能测试

- 运行 `scripts/run_campus_agent_smoke_windows.py` 对固定合成助学申请记录做一次 DeepSeek `deepseek-flash` Agent 调用。问题涉及 `SIM-REC-001`，身份为 `SIM-USER-001`；未使用真实学生资料。
- 总计两次模型 invocation、输入 2,012 tokens / 输出 173 tokens；usage 全部可用。按项目峰值单价且输入均视为缓存未命中的估算，费用 US$0.0008112，真实账单以服务商记录为准。
- 模型实际调用 `query_application_status(record_id=SIM-REC-001, service_type=aid_application)`；本地模拟工具结果为 found，运行脚本核验记录号、状态与 `simulation_only=true` 均匹配。
- 证据：`runs/campus-agent-smoke-20261006-205048/manifest.json`；逐次 usage 已追加到 `reports/API_USAGE.jsonl`。脚本确认不是人工评分/答案 Judge，也不替代完整浏览器 UI 体验。

## 累计用量快照与人工项

- 当前 `reports/API_USAGE.jsonl`：275 条记录，输入 690,137 / 输出 36,427 tokens；保守估算 US$0.2508582；实际账单未知。Coze 调用数仍为 0。
- 运行时服务/UI 与模型链路已自动验证；H-05 仍需负责人亲自用 Windows 浏览器核对内容观感并保存截图。H-01 仍需轮换曾在对话中暴露的 API Key；H-02/H-03/H-04/H-07 按 `reports/HUMAN_TODO.md` 执行。

## 验收标准

- 当前自动范围：FastAPI、校园 Agent 注册、Streamlit HTTP 健康/页面、合成身份 UI、fake 对话、一个真实模型到模拟状态工具的路径及 usage 记录均通过。
- 当前不覆盖：浏览器人工视觉验收、截图、Coze、10 行人工评分、教师许可、真人数据或工单。
