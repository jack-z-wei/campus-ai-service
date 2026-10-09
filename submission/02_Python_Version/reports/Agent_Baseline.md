# 校园 Agent 基线记录

日期：2026-10-06（Asia/Shanghai）。我先用真实模型做了单例和多轮运行，记录模型选择工具的过程及实际 trace。后续的冻结集四层评测另见 `Agent_Evaluation.md`。

## 实现分支

| 分支 | 编排与存储 | 当前能力 | 独立性说明 |
|---|---|---|---|
| Python 原理版 | 本项目显式 RAG 顺序、NumPy cosine、HTTPX Chat Completions、Pydantic schema/ToolRegistry/Executor；SQLite bounded conversation memory | 单轮知识问答、状态和转人工真实 Function Calling；每 session 最近 4 组成功问答；工具调用总数上限 4，每次模型响应最多 2 个 | 不调用 LangGraph Agent；复用校园来源/向量、SQLite 状态函数和 Prompt |
| 工程版 | 固定上游 LangGraph `StateGraph + ToolNode + RemainingSteps`，上游 AsyncSqliteSaver checkpoint | 校园 Agent 注册、模拟身份 Runtime 注入；真实多轮状态查询、跨轮转人工；模型上下文限制最近 4 轮；会话可按 thread 清除 | 模式和 thread saver 来自 `JoshuaC215/agent-service-toolkit`；针对性删除 API 和校园上下文窗口为本项目改动；范围见 `UPSTREAM.md` |

上游模板的通用 RAG 工具和托管检索不适合直接用于本项目的校园来源范围与 NumPy 原理版。我检查了模板里的 retriever，发现它只取固定 Top-K，不会沿校园资料的原文位置补回相邻文本。K01 遇到句子被分块截断后，我就在原理版中加入了可追溯的相邻块延展。

## 已留存的真实模型运行

| 运行 | 真实观察 | 用量与费用估算 | 当前判定 |
|---|---|---|---|
| 原理版 K01，首次 Top-5 | 1 次模型调用，得到 15–35 学分和 2022 caveat，但额外审批结论在提供给模型的首块中被截断 | 输入 3,311 / 输出 211 tokens；US$0.0012465 | 内容命中 gold 主答复，但 groundedness 有实际失败，不计完全通过 |
| 原理版 K01，严格提示重跑 | 提示要求不可补全截断句，模型仍补充首块未呈现的审批细节 | 输入 3,350 / 输出 206 tokens；US$0.0012522 | 真实提示优化失败，记录保留 |
| 原理版 K01，补连续块后 | Top-1 邻接上下文增加 420 个字符，去重 80 字符；模型答案中的审批句可在实际上下文中找到 | 输入 3,743 / 输出 214 tokens；US$0.0013797；1 次模型请求 | 单例有来源支持；其余 20 题和人工评价待做 |
| 原理版 S01，原工具 schema | 用户只说 SIM-REC-001，模型要求额外提供服务类别，未调用工具 | 输入 3,526 / 输出 31 tokens；US$0.001095 | Agent 选择/任务完成失败，trace 保留 |
| 原理版 S01，身份范围内解析类别后 | 状态函数由受控 `SIM-USER-001` 与模型给出的 `SIM-REC-001` 查到本人唯一行；模型调用状态工具并返回“材料审核中” | 输入 3,560 + 3,700 / 输出 51 + 103 tokens；US$0.0023628；2 次模型请求、1 次工具调用 | 合成记录结果正确。实际工具参数只含 `record_id`，比冻结 gold 少 `service_type`；精确参数分数不能自动判全对 |
| 工程版校园 Agent smoke | 真实模型调用 `query_application_status`，返回 SIM-REC-001 的材料审核中状态 | 原 trace 与成本见 `runs/campus-agent-smoke-20261006-175330/manifest.json` | 验证一次图内工具路由，不等于固定集通过 |

## 双路线真实多轮 Memory 与工具复测

我分别在原理版和工程版运行了 M01、M02。每组使用独立的 synthetic identity/session，不复用其他组的历史。下面记录的是这四组运行的实际表现，其余用例结果见冻结集评测。

| 路线/用例 | 实际表现 | 模型用量 / 峰时估算 | 判定与证据 |
|---|---|---|---|
| 原理版 M01 | 第 1 轮追问编号、0 次工具调用；第 2 轮的 memory 记 1 个 prior turn，并调用 `query_application_status(record_id=SIM-REC-001, service_type=aid_application)`，得到“材料审核中”。 | 3 次响应；输入 9,175 / 输出 200 tokens；US$0.0029925 | 两轮标准完成；`runs/principles-multiturn-20261006-184014-e3debe8c/` |
| 原理版 M02 | 第 1 轮查到 SIM-REC-002“已派单”；第 2 轮 memory 记 1 个 prior turn，调用转人工工具并创建 ticket `SIM-TICKET-ce1b980498875ed2`；DB owner 为 SIM-USER-002，状态 `created_simulated`，没有联系真人。 | 4 次响应；输入 13,895 / 输出 399 tokens；US$0.0046473 | 两轮工具选择、数据库写入与模拟标记通过；`runs/principles-multiturn-20261006-184055-dedf150d/` |
| 工程版 M01 | 同一上游 SQLite checkpoint thread 持有两轮；第 1 轮追问，第 2 轮带有一轮历史并查询状态；响应正确。测试 thread 在保存 trace 后由 `adelete_thread` 清除。 | 3 次响应；输入 2,964 / 输出 186 tokens；US$0.0011124 | 两轮完成；`runs/engineering-multiturn-20261006-184452-62342997/` |
| 工程版 M02 | checkpoint 保存第一轮的 4 条消息；第 2 轮模型上下文窗口为 1 个用户轮次，调用状态/人工工单工具并创建 ticket `SIM-TICKET-09fca15ada3e5a55`。结果明确 `simulation_only=true`、`real_human_contacted=false`。 | 4 次响应；输入 4,687 / 输出 455 tokens；US$0.0019521 | 两轮完成；`runs/engineering-multiturn-20261006-184518-5069f94b/` |

我还用临时 SQLite 检查了原理版的最近 N 轮裁剪、session/user 隔离、越权读写拒绝和所有者清空。CLI 清空后返回 `cleared`，history 为空，也没有调用聊天 API；记录见 `runs/principle-memory-clear-cli-smoke-20261006/manifest.json`。工程版则通过真实 SQLite saver 检查 thread 删除：本人 thread 删除后从列表消失，跨用户请求返回 404，且不会删除对方记录。对应测试记录见 `tests/service/test_threads_sqlite.py`。

本任务四组真实多轮新增 14 次模型响应、输入 30,721 / 输出 1,240 tokens，峰时估算 US$0.0107043；累计全项目 49 次模型响应、输入 109,734 / 输出 6,911 tokens，峰时未命中缓存总估算 US$0.0413181。账号实际账单未核实。Coze 请求仍为 0。

费用按记录时核对的 DeepSeek 峰时单价估算，并把输入都按缓存未命中计算。逐次 usage 见 `reports/API_USAGE.jsonl`，请求事件见 `reports/API_REQUEST_EVENTS.jsonl`。这只是估算，不是账号账单；这部分实验没有调用 Coze。

## 工具和边界

- 三个工具固定为 `search_campus_knowledge`、`query_application_status`、`create_human_service_request`。知识搜索 Top-5 为服务端常量；模型 schema 不包含模拟用户身份、文件系统路径或数据库路径。
- `query_application_status` 必须在执行时从服务配置拿当前 SIM 身份，SQL 绑定当前用户与记录号；有服务类别时一并过滤。省略类别时，后端只在已认证的模拟用户范围内解析该编号，不按其他用户编号枚举。
- 状态结果和人工工单均标明 simulation；工单不联系真实人员。重复请求使用有界 request scope 的幂等键。
- 原理版工具执行每模型轮最多 2 个调用，总计最多 4 个工具调用和 5 次模型请求；超限时直接返回上限状态，不伪造工具结果。
- 模拟身份仍不是登录认证。本地的用户隔离只在课程演示 SQLite 数据上验证，不构成真实校园服务授权系统。

## 后续冻结集评测

此前“待评测范围”是单例与多轮阶段的历史状态。之后已按冻结集基线与优化版分别完整运行两路线，每路线 21 个案例、23 个 assistant turns；对照、逐轮 traces、Judge 输入和局限见 `reports/Agent_Evaluation.md` 与 `TASK/TASK-013.md`。

- S01 冻结 gold 仍要求 `service_type=aid_application`。基线、优化结果按原 gold 记录；Principles 优化版 S05 另有一次省略 `service_type` 的真实参数指标退化。
- S04 无身份时不再暴露个人状态工具；跨身份 checkpoint 污染问题由另一个真实 SQLite graph integration regression 捕获并修复。
- U02 仍只命中两个 gold 来源中的一个，Recall@5=0.5。重复运行不等同于多个不同检索失败场景。
- B01 模型两版都直接安全拒绝、没有调用要求返回 forbidden 的状态工具，留下冻结 gold 与安全行为的合同差异。
- V1/V2 的 10 份回答另按统一 Rubric 评分，各 30/30，逐项理由与 trace 见 `reports/评分表_V1_V2.csv`。自动 Judge 与 Rubric 分项结果分别保存。
