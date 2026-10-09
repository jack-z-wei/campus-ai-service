# Day 1 实施检查点

日期：2026-10-06（Asia/Shanghai）

这是进入固定集 Evaluation 前的真实状态快照，不是最终验收报告。现有失败、未核验项和人工待办继续保留。

## 阶段状态

| 任务 | 当前状态 | 证据/待办 |
|---|---|---|
| TASK-001～002：环境、需求和依赖 | Windows Python 3.12.7 项目 `.venv`、锁依赖、真实 DeepSeek 与 Ollama 检查通过；Coze 和上游课程许可仍需用户核验 | `reports/WINDOWS_ENVIRONMENT.json`、`reports/EXTERNAL_DEPENDENCIES.md`、`UPSTREAM.md` |
| TASK-003～004：数据与冻结验收 | 14 份官方资料、4 类主题；21 个冻结题和状态工具契约均已绑定来源版本 | `docs/campus/source_manifest.json`、`evaluation/frozen_cases.json` |
| TASK-005～006：RAG/Prompt 基线 | 三种 Chunker、真实 BGE-M3 1024 维向量、NumPy/Chroma；10 题检索、V1/V2 各 5 题和 U01/U02真实运行 | `reports/RAG_Baseline.md`；U02 Recall@5=0.5 的来源缺失失败仍在 |
| TASK-007：Agent 与业务工具 | 上游 LangGraph 工程 Agent、身份 Runtime、参数化 SQL 与本地工单；状态和人工转接都已被真实模型选择。尚缺固定集和浏览器端到端可视 Trace | `reports/Agent_Baseline.md`、`TASK/TASK-007.md` |
| TASK-008：Memory | 原理版 SQLite 最近 4 轮；工程版上游 SQLite checkpoint + 最近 4 轮模型上下文；两路线 M01/M02 真跑，清空、身份隔离和 thread 删除测试通过 | `TASK/TASK-008.md` 与四个 `runs/*multiturn*` 目录 |
| TASK-009：Coze | 上传材料包通过 Windows 检查；平台账号、价格、权限和实际运行未确认，也没有 Coze 调用 | `coze/`、`TASK/TASK-009.md`、H-02 |
| TASK-010：固定集 Evaluation | 下一项工作；指标规范和可重算原始报告尚待实现 | `evaluation/frozen_cases.json` |

## Memory 多轮结果

- M01/M02 各在原理版、工程版运行一次，4 组实验共 14 次 DeepSeek 响应；输入 30,721、输出 1,240 tokens，按峰时未命中缓存估算 US$0.0107043。
- 两个 M01 都在缺记录号时追问，之后查询 SIM-REC-001 并返回模拟“材料审核中”。
- 两个 M02 都先查到 SIM-REC-002“已派单”，再跨轮调用转人工工具；ticket 分别为 `SIM-TICKET-ce1b980498875ed2` 与 `SIM-TICKET-09fca15ada3e5a55`。它们是本地模拟记录，未联系真人。
- 清空会话的原理版 CLI 用隔离 SQLite 文件跑通并核实 history 为空；工程版 API 的真实 SQLite checkpointer 测试验证本人 thread 删除成功、跨用户删除被拒且对方记录保留。
- 相关 Windows 定向套件：46 passed、6 warnings；Ruff 和 `py_compile` 通过。完整仓库测试和全固定集还未跑。

## 使用量与限制

截至 2026-10-06 18:45，共 49 次 DeepSeek 响应；服务返回 usage 合计输入 109,734、输出 6,911 tokens。按峰时输入未命中缓存单价估算 US$0.0413181；实际账单、余额和充值状态未知。逐请求原始估算见 `reports/API_USAGE.jsonl`。Coze 调用与收费请求均为 0。

项目中的用户、申请和工单全是合成数据。DeepSeek Key 不写入源代码或运行 manifest；该 Key 曾贴在聊天中，项目收尾后应从控制台撤销并在 Windows `.env` 更新新 Key。

## 已知缺项

- `runs/rag-unknown-v2-20261006-180143/` 中 U02 的第二个期望来源未命中；正确拒答不等于检索通过。
- K01 截断上下文已经增加同源相邻块后补测；仅有 K01 单题证据，不能推断全量回答忠实性。
- 原理版 S01 第一次未调用工具，调整服务端按身份解析记录类别后重跑成功；冻结 gold 的精确参数差异没有改写。
- V1/V2 回答评分待 H-03；Coze 工作区和费用待 H-02；上游模板课程许可待 H-07。
- 当前还没有 21 题四层基线、至少三项审计支持的优化对照、真实 Coze 输出或最终报告提交包。

## 下一阶段验收

先实现和校验四层指标，再分批跑冻结集并保存可重算 trace。保留失败原样，按实测工程问题决定改进项；H-02、H-03、H-07 不阻塞无关本地工作。
