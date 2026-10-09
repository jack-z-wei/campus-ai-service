# 《基于 RAG 与 Agent 的校园智能客服系统》课程设计报告

> **版本：V1.2；生成日期：2026-10-09。** 这份报告记录我完成课程设计的过程和结果，依据项目代码、运行记录、测试结果及来源材料整理。项目实现中使用了 Codex 辅助，工具使用情况见第三十章。Coze 部分实际运行了 14 道题、16 个助手轮次，并比较了 A/B 知识库和检索参数；平台没有提供实际费用和部分逐轮工具记录。两条本地路线按 21 个冻结用例进行评测，多轮对话按助手回复轮次另计，因此与模板中的 20 题口径不同。2026-10-08 的双路线复跑、模型评估和工程版浏览器截图也已收录。

---

# 一、基本信息

| 项目 | 内容 |
|---|---|
| 课程名称 | 人工智能课程设计 |
| 实验项目 | 基于 RAG 与 Agent 的校园智能客服系统 |
| 学生姓名 / 学号 | 章峻炜 / 2023900904 |
| 指导教师 | 宋清松 |
| 项目开始日期 | 2026-09-20 |
| 项目完成日期 | 2026-10-06 |
| 报告版本 | V1.2 |
| Git 仓库 / 项目路径 | [GitHub 公开仓库](https://github.com/jack-z-wei/campus-ai-service)； `campus-ai-service`

### 项目组织方式

这是个人项目，没有小组成员或小组分工。项目开发中使用了生成式 AI 辅助工具，具体用途见第三十章。

---

# 二、项目摘要

## 2.1 项目简介

我把校园客服的功能分成公开资料问答、合成申请状态查询、模拟人工转接、多轮对话和未知问题处理，并做了三条实现路线：Coze、Python/NumPy 原理版和 LangGraph 工程版。Coze 中建立了 A/B 两个知识库和合成状态表，并配置了校园客服 Agent、状态查询与模拟工单工作流。14 道题的实际运行结果和 A/B、检索参数、三轨对照分别留有记录。平台没有提供实际账单和完整的逐轮工具记录。校园知识库收录了 14 份公开资料；申请状态和工单均为合成数据，不连接学校业务系统。

原理版使用 Ollama BGE-M3、NumPy cosine 检索、HTTPX 和 Pydantic 工具注册；工程版使用 FastAPI、Streamlit、LangGraph、Chroma 和 SQLite checkpoint。两条本地路线都运行了 21 个冻结用例，每条路线产生 23 个助手回复轮次，并保存 trace、manifest 和四层指标。我在 Codex 辅助下修复了身份隔离和 Chroma 并发冷启动问题；U02 来源召回不足、B01 的工具调用金标准冲突，以及 Principles 参数分数下降仍未消除。V1/V2 各 5 份回答由 Codex 按统一 Rubric 评分，均为 30/30；评分理由和原始记录见评分表。
2026-10-08 在 Windows 项目环境再次运行两条本地路线的 21 个冻结案例（多轮共 23 个回答单元），对新鲜单轮记录和与当前代码指纹完全匹配的历史多轮记录分别留存。首次工程复跑暴露 Chroma 冷启动并发初始化缺陷；改为锁保护的单例初始化后，在修复版重跑完整 21 案例，工程版运行错误率为 0/23。新一轮离线指标与 46 条 Judge 评分见 `runs/e2e-20261008-metrics-v3/metric_results.json`；Judge 与生成使用同一模型系列，结果结合原始响应解释。

## 2.2 项目核心技术

| 技术模块 | 实际技术 | 版本 / 配置 | 用途 |
|---|---|---|---|
| LLM | DeepSeek `deepseek-flash` | provider usage 可见的专用运行记入 usage 日志；通用 UI `/invoke` 不返回 usage | 生成回答、选择业务工具、模型辅助 Judge |
| Embedding | Windows 本机 Ollama `bge-m3:latest` | 1024 维；批量 8 | 校园文本和查询向量化 |
| Knowledge Base | 14 份来源清单绑定的 Markdown 快照 | UTF-8；source manifest SHA-256 | 课程问答语料和时间/适用范围约束 |
| Vector Store | Python 原理版 NumPy；工程版 Chroma | cosine 检索；Top-K=5 | 返回候选片段和来源 |
| RAG | 显式检索、上下文构造、来源范围过滤、引用提示 | V1/V2 prompt 实验 | 降低无来源回答，并拒答超出语料边界的问题 |
| Tool | `search_campus_knowledge`、`query_application_status`、`create_human_service_request` | Pydantic / LangChain schema；SQLite 合成数据 | 知识检索、限身份查模拟记录、创建模拟工单 |
| Agent | Python 显式 ToolRegistry；LangGraph `StateGraph` / `ToolNode` | 上游工程基座固定提交见 `UPSTREAM.md` | 规划工具调用、传递观察结果和结束回答 |
| Memory | SQLite 会话记忆；上游 AsyncSqliteSaver | 模型上下文窗口最多最近 4 轮 | 多轮追问、thread 保存与清除 |
| Evaluation | 本项目四层指标、21 例冻结集、pytest | `metric_spec_v1.json` v1.1 | 检索、回答、Agent、工程结果分开统计 |
| 可视化平台 | Coze | 个人空间中的知识库、表、两个工作流和 Agent 配置均有实测证据；模型/Embedding 费用与平台账单未核验 | A/B 知识库、模拟状态表、14题/16轮预览、检索参数对照及 K01/S02 三轨同题结果 |
| 工程辅助工具 | Codex | 项目迭代与文档整理 | 协助代码实现、问题分析和材料整理 |
| 语言 / 运行环境 | Python | Windows Python 3.12.7；Windows `.venv` | 源码、服务和测试运行环境 |
| 数据库 | SQLite | 合成申请/工单与 checkpoint | 本地演示数据、会话状态持久化 |

---

# 三、项目需求分析

## 3.1 应用场景

场景是校园公开信息与课程演示数据的统一问答入口：用户可问某个公开办法的内容，查找自己指定的合成记录状态，也可以要求创建模拟人工服务请求。知识回答必须同时受文件年份、适用对象和当前效力标签约束；例如 2017 年来华国际学生校外住宿办法不能推断为中国籍本科生规则。状态查询以服务端注入的 `SIM-USER-###` 限定数据库 owner，不能仅凭聊天里给出的记录号跨用户读取。创建工单只在项目 SQLite 中写入 `created_simulated` 记录，不通知真人。

## 3.2 用户需求

| 编号 | 用户需求 | 类型 | 实现状态 |
|---|---|---|---|
| R1 | 查询可追溯的教务、奖助、宿舍和图书馆公开信息 | Knowledge | 本地两路线和 21 例已运行；U02 有召回缺口 |
| R2 | 依据明确记录号查询本人演示状态 | Tool | 合成身份范围内真实 Function Calling 已运行 |
| R3 | 明确请求人工跟进时创建本地模拟工单 | Tool / Agent | M02 两路线已运行；不联系真实人工 |
| R4 | 缺少编号时追问，并在下一轮继续查询 | Memory | M01 两路线真实多轮通过 |
| R5 | 资料不足时说明边界，不编造政策或时间 | Unknown | U01/U02 已运行；U02 来源补全不足 |
| R6 | 不同模拟身份的对话不能互相污染 | Safety / Engineering | 图级 identity scope 修复；SQLite integration 回归通过 |

## 3.3 功能需求

- 知识问答：返回回答、引用来源、发布日期和适用范围；来源排序实验与四层回答评测分开。
- 业务查询：仅使用当前可信运行配置中的模拟身份查询本人合成申请，不将身份字段交给 LLM 生成。
- 人工转接：经明确用户请求创建本地 `simulation_only` 工单；不承诺真人收到或上门时间已确定。
- 多轮对话：两条路线都能追问记录号并在下一轮调用工具；上下文最多带最近 4 轮。
- 未知问题：证据不足时不补出确定政策；U02 目前只检索到其两个 gold 来源之一，需联系现行信息渠道而不能外推。
- 来源引用：在 RAG 回答中展示实际来源；Judge 结果只是同系列模型代理。

## 3.4 非功能需求

| 维度 | 当前实现与观察 |
|---|---|
| 响应时间 | 冻结集保存逐轮延迟；Principles 与 Engineering 的计时范围不同，分别报告而不跨路线排名。 |
| 稳定性 | 最新修复版 21 个用例/路线均有 23 个 turn，0/23 路由执行错误；项目 Windows pytest 244 passed、4 skipped。 |
| 安全性 | SQL 参数化、owner 约束、身份感知 schema、ToolNode 前敏感工具白名单；模拟 ID 不等于真实认证。 |
| 可复现性 | 固定来源/冻结集/Prompt/代码指纹，保存原始 trace、Judge 输入、用量与 run ID。 |
| 可维护性 | 本地 RAG、工具、记忆、评测模块按职责分开；依赖锁在 `uv.lock`。 |
| 可扩展性 | 通用上游 Agent 服务保留，但接入生产校园身份、政策数据库或真实工单需另行鉴权与隐私审查，当前不具备。 |

---

# 四、总体系统架构

## 4.1 系统总体架构图

```mermaid
flowchart LR
    U[演示用户] --> UI[Streamlit]
    UI --> API[FastAPI / AgentClient]
    API --> ENG[LangGraph 工程版]
    CLI[Python 原理版 CLI] --> PR[显式 RAG + ToolRegistry]
    ENG --> RETC[Chroma]
    PR --> RETN[NumPy cosine]
    RETC --> OLL[Ollama BGE-M3 本机]
    RETN --> OLL
    RETC --> SRC[14 份来源快照]
    RETN --> SRC
    ENG --> LLM[DeepSeek Flash]
    PR --> LLM
    ENG --> DB[(SQLite 合成记录/工单)]
    PR --> DB
    ENG --> CP[(SQLite checkpoint)]
    PR --> MEM[(SQLite bounded memory)]
    ENG --> TRACE[runs manifest / trace]
    PR --> TRACE
    EVAL[四层 Evaluation] --> TRACE
```

可编辑源图：[`system_architecture.mmd`](system_architecture.mmd)。SQLite 中仅为课程合成记录。Coze 是独立的平台路线；其配置截图已归档，但没有与本地架构画成已连接组件。

## 4.2 系统工作流程

```text
输入问题、thread/session 与合成身份
 → 检查身份边界和可用工具
 → 知识类：Ollama 查询向量 → source-policy 检索 → 必要时延展相邻同源块 → LLM 回答与引用
 → 状态/工单类：LLM 选择结构化工具 → 再检查 allowlist 和可信身份 → owner 范围 SQL 读/写
 → 工具结果进入下一轮模型上下文 → 最终答复
 → 保存实际检索来源、工具参数/结果、usage、延迟、错误和代码/数据指纹
```

我保存了 Windows 浏览器首页截图，并记录了真实模型工具调用和自动化界面检查（TASK-017/018/020）。流程图源：[`request_flow.mmd`](request_flow.mmd)。

---

# 五、数据与知识库建设

## 5.1 知识库来源

我整理了 14 份长安大学公开网页和 PDF 快照，并在来源清单中登记官方 URL、抓取或发布日期、适用范围、检索策略及 SHA-256。完整信息保存在 source_manifest.json 和 Coze 导出的 source_manifest.csv 中。

| Source ID | 文档 / 主题 | 日期或版本 | 使用边界 |
|---|---|---|---|
| `academic_course_selection_2022` | 本科生选课及修课管理办法 | 2022-09-15 | 2022 试行办法，现行效力待教务处复核 |
| `academic_status_2022` | 本科生学籍管理规定 | 2022 版 | 历史版本，现行效力待复核 |
| `aid_portal_2025` | 学生资助信息公开目录 | 页面含 2025 更新条目 | 只回答目录明确展示的信息 |
| `aid_national_grant_2021` | 本科生国家助学金评审办法（修订） | 2021-06-28 | 历史版本，不断言当前金额/时间 |
| `aid_work_study_2025_listing_2016_text` | 勤工助学管理办法 | 目录 2025；正文 2016；HTTP 日期 2021 | 日期版本有冲突，已标记复核 |
| `student_management_2017` | 学生管理规定 | 2017-08-09 | 仅指出宿舍事项另有规定，未提供国内本科生校外住宿流程 |
| `student_summer_notice_2026` | 2026 暑期学生工作通知 | 2026 暑期 | 仅适用该暑期，不当作常年规则 |
| `student_fall_notice_2026` | 2026 秋季开学本科生教育管理通知 | 2026 秋季 | 仅适用该学期开学工作 |
| `international_off_campus_housing_2017` | 来华留学生校外住宿管理办法 | 2017-10-26 | 明确仅适用来华国际学生 |
| `campus_fire_safety_2012` | 消防安全管理规定 | 2012-06-30 | 历史规定，效力待核验 |
| `library_home_2026` | 图书馆官网主页动态快照 | 抓取 2026-10-06 | 联系方式/公告导航；无开放时段内容 |
| `library_archive_hours` | 图书馆旧版开放时间页面 | 未标日期 | `archive_not_for_current_answers` |
| `library_archive_reader_rules` | 图书馆旧版读者须知 | 未标日期 | 不冒充当前借阅规则 |
| `library_archive_remote_access` | 图书馆旧版校外访问页 | 未标日期 | 不据此确认当前远程访问方式 |

## 5.2 知识库规模

| 指标 | 实测值 |
|---|---:|
| 文档数量 | 14 |
| 主题数量 | 4：教务、奖助、宿舍、图书馆 |
| 文档总字符数（本地 UTF-8 快照） | 58,621 |
| 分块实验样本数 | 固定/递归/标题策略合计 475 个策略版本块；不是 475 篇原始文档 |
| 固定 500/80 索引 | 147 chunks；平均 470.05 字符；最大 500 |
| Embedding 维度 | 1024 |

我在 Windows 项目 .venv 中读取登记的来源快照并计算了这些数据；首次向量化记录保存在 `runs/campus-index-20261006-173801/manifest.json`。

## 5.3 文档清洗

我先把 PDF 和 HTML 原文整理成独立的 UTF-8 文本快照，再登记 source ID、URL、发布日期、适用对象、效力范围、index_policy 和 SHA-256。Loader 只读取清单中登记的文件，并会拒绝越界或哈希不一致的来源。整理时我尽量保留标题、列表、链接、日期和 PDF 页码；旧图书馆页面仅用于检索对照，版本冲突和适用范围不明的材料也单独标出。

---

# 六、Chunking 实验

## 6.1 Chunk 策略

| 方案 | 最大长度 | Overlap | 切分方式 | 数量 / 平均长度 |
|---|---:|---:|---|---:|
| A | 500 字符 | 80 字符 | 固定窗口 | 147 / 470.05 字符 |
| B | 500 字符 | 80 字符 | 段落、换行、句末标点等递归边界 | 213 / 338.19 字符 |
| C | 700 字符 | 0（实现不重复拼接前块） | Markdown 标题路径 + 章节内递归分段 | 115 / 508.22 字符 |

## 6.2 Chunk 实验结果

我先用 K01、K10 和 U01 比较固定长度、递归边界和标题结构三种切分。未过滤归档来源时，三种策略的 MRR@5 分别为 0.511111、0.333333、0.416667；过滤后均为 1.000000，固定索引的 Chroma 结果也为 1.000000。这三题只用于初步参数观察。

| Query | 固定窗口 A | 递归边界 B | 标题结构 C |
|---|---|---|---|
| K01 每学期修课学分 | 期望办法排名 1 | 三题过滤后 MRR 总体计入 1.0 | 三题过滤后 MRR 总体计入 1.0 |
| K10 图书馆联系方式 | 过滤后主页排名 1；未过滤时旧读者须知先于主页 | 过滤后期望来源排名 1 | 过滤后期望来源排名 1 |
| U01 当前开放时间 | 可检索主页，但主页不含具体时段 | 不能由分块本身补出缺失信息 | 不能由分块本身补出缺失信息 |

详细逐题排名：`runs/chunking-compare-20261006-174049/manifest.json` 与 `runs/retrieval-frozen10-20261006-180107/per_case.jsonl`。

## 6.3 分析

从这次结果看，chunk 太大时会把无关段落和旧版本一起送给模型，增加输入长度，也容易混淆适用范围；chunk 太小则可能切断审批条件或限定语。Overlap 能缓解片段边界问题，但会增加重复文本和向量数量。固定 500/80 便于复现本地索引，但 K01 的实际失败说明固定窗口仍会截断句子。为此，我在原理版加入了同源连续块扩展，并在 trace 中记录补入位置。旧来源过滤改善了这批小样本排序，但语料没有覆盖的问题仍然存在。

---

# 七、Embedding 与向量检索

## 7.1 Embedding 配置

| 项目 | 配置 |
|---|---|
| 模型 | Ollama `bge-m3:latest`，运行于 Windows 本机 `127.0.0.1:11434` |
| 向量维度 | 1024 |
| Distance Metric | cosine similarity（本地 NumPy 验证） |
| Batch Size | 8；固定索引实际 19 批 |
| 收费请求 | Embedding 走本地 Ollama；索引任务 manifest 标 `paid_api_request_performed=false` |

## 7.2 Retrieval 配置

| 参数 | 最终本地值 |
|---|---|
| Top-K | 5 |
| 相似度阈值 | 当前评测口径为 Top-K 排名；未设置单一拒答分数阈值 |
| Reranker | 无 |
| Hybrid Search | 无 |
| 来源策略 | 排除 `archive_not_for_current_answers`；按来源 ID 聚合排名 |
| K01 上下文补块 | 首块不完整时只补同源下一个连续 chunk，并去重字符重叠 |

## 7.3 Retrieval 示例

| Query | Top-1 | Top-3 | Top-5 | 正确来源位置 |
|---|---|---|---|---|
| K01 每学期学分（10 题基线） | 期望来源命中 | 命中 | 命中 | `academic_course_selection_2022` rank 1 |
| K10 图书馆联系方式（未过滤索引） | 旧 reader rules | 旧 hours / 主页 | 主页在 rank 3 | `library_home_2026` rank 3 |
| K10（来源过滤后） | 主页 | 命中 | 命中 | `library_home_2026` rank 1 |
| U02 中国籍本科生校外住宿流程 | 国际学生 2017 办法 | 无第二 gold 来源 | 无第二 gold 来源 | 两个期望来源仅命中一个，Recall@5=0.5 |

我随后用 K01–K10 做了完整检索评测。NumPy 和 Chroma 的 Recall@1/3/5、MRR@5 均为 1.0。21 例 Agent 冻结集另含 U01、U02，两组分母不同；这两类结果需要分开看。

---

# 八、RAG 系统实现

## 8.1 RAG 流程

实际回答时，我先按冻结来源查询，再用 Ollama 生成问题向量，由 NumPy 或 Chroma 返回 Top-5 片段，并应用来源时效策略。原理版还会检查首个高分片段是否被截断，只从同一来源补入连续片段。Prompt 要求模型依据实际检索内容回答并说明来源日期、适用范围和未知边界。每次运行都会保存答案、来源、工具结果、usage、耗时及代码和数据指纹，便于复算。

## 8.2 Prompt 设计

两版 System Prompt 存于 `prompts/campus_system_v1.md` 和 `prompts/campus_system_v2.md`，同一组 K01、K05、K06、K09、K10 各真实运行一次。

核心结构要求：用当前检索文本作依据；明确指出旧政策和适用人群；不把国际学生规定推广到其他学生；来源缺失时说明无法确认并提供可核验方向；状态必须来自状态工具；用户未明确要求时不创建模拟工单；所有状态/工单说明“课程模拟数据”，不得暗示连接真实校园系统。

在这五道题中，V1 和 V2 的检索指标都是 1.0。V2 的“答复/依据”格式出现在 5/5 个回答中，V1 为 0/5。V2 输出 token 多 29.09%，按同一口径估算的费用多 17.13%。我还按统一 Rubric 给 10 份回答评分，两版各 30/30；这个结果只描述当前样本，不能说明 V2 总体更优。评分明细见评分表 V1_V2.csv。

## 8.3 Unknown Handling

我也用 U01 和 U02 检查了资料不足时的处理。U01 的官网首页快照没有开放时段，系统没有拿旧页面推断当天时间。U02 的旧住宿办法只适用于来华国际学生，系统没有将它外推到中国籍本科生；但检索只命中两个 gold 来源中的一个。拒答边界处理较稳妥，来源召回仍未通过，我把 U02 保留为缺陷。

---

# 九、Tool 设计与实现

## 9.1 Tool 清单

| Tool | 功能 | 关键输入 | 输出 | 数据来源 |
|---|---|---|---|---|
| `search_campus_knowledge` | Top-5 校园资料搜索 | query | source ID、rank、标题、URL、范围、文本 | manifest 登记的公开快照和本地索引 |
| `query_application_status` | 查本人合成申请状态 | `record_id`、可选 `service_type`；可信模拟身份由运行端注入 | found/not_found/invalid_identity/forbidden 和模拟状态字段 | 本地 SQLite 合成状态表 |
| `create_human_service_request` | 创建模拟人工服务请求 | service type、原因、可选关联 record；可信 owner 和去重上下文由服务注入 | ticket ID、时间、created_simulated 标记 | 本地 SQLite 合成工单表 |

## 9.2 Tool Schema

简化示例（实际 schema 见 `src/campus/principle_tools.py`、`src/campus/tools/langchain_tools.py`）：

```json
{
  "name": "query_application_status",
  "description": "Query one status record inside the authenticated synthetic user's scope.",
  "parameters": {
    "type": "object",
    "required": ["record_id"],
    "properties": {
      "record_id": {"type": "string"},
      "service_type": {
        "type": "string",
        "enum": ["aid_application", "scholarship_application", "dorm_repair", "library_service"]
      }
    },
    "additionalProperties": false
  }
}
```

`simulation_user_id`、数据库路径、认证 owner 不是模型参数。status 工具由服务器以 `owner_user_id` 和 record ID 参数化查询；若类别存在则额外过滤类别。

## 9.3 Tool 测试

| 测试类型 | 输入/边界 | 预期 | 证据 / 结果 |
|---|---|---|---|
| 正常查询 | SIM-USER-001 + SIM-REC-001 | 本人助学记录材料审核中 | `tests/campus/`；S01/M01 trace 实际找到合成行 |
| 正常查询 | SIM-USER-002 + SIM-REC-002 + dorm_repair | 本人宿舍工单已派单 | S02 优化版两路线 trace 均调用 status tool 成功 |
| 越权查询 | SIM-USER-001 请求 SIM-USER-002 的 SIM-REC-002 | 不返回对方状态 | 状态层返回 forbidden；Agent 冻结任务层仍记录 B01 gold 合同冲突 |
| 不存在 | SIM-USER-001 + SIM-REC-999 | not_found；不得编造状态 | status tool 合约测试和 S05 frozen trace |
| 无可信身份 | 仅发记录号 | 不调用个人业务工具 | S04 优化 trace 与身份门控测试 |
| 工单创建 | 明确要求转人工；SIM-USER-002 | 创建本地唯一模拟工单，不联系真人 | 两路线 M02 第 2 轮记录创建成功 |

项目 Windows 环境的最新全量测试为 244 passed、0 failed、4 skipped；4 个 Docker 标记用例按默认设置跳过。测试和运行证据索引见 `tests/campus/` 与 `runs/`。

## 9.4 Tool 设计分析

我把知识检索和业务操作分开处理：检索工具返回证据文本，状态和工单工具由确定性后端执行。Owner 从运行配置注入，SQL 使用参数化查询；模型不能靠记忆或臆测提供状态。工具失败时，回答也必须说明失败或请用户补充信息。课程演示用的 SIM 身份不是校园登录认证，不能用于生产服务。

---

# 十、Agent 设计与实现

## 10.1 Agent 架构

原理版按顺序执行 RAG 预处理、模型请求、Function Call 解析、Pydantic 校验、ToolRegistry 执行、工具结果回传和下一轮生成。我保留这条路线，是为了展示 Agent 的基本调用过程；它不调用 LangGraph。

工程版基于上游 Agent Service Toolkit 的 StateGraph、ToolNode 和 RemainingSteps 接入校园 Agent、工具 schema 与模拟身份运行时上下文。两条路线共用校园来源、合成业务数据和冻结标准，但 Agent 的实现彼此独立。

## 10.2 Agent 决策规则

- 直接回答：常识性短问或已有充分上下文的追问；涉及学校规则需有检索证据。
- 查询 Knowledge：规则、日期、来源和联系方式问题调用检索；必须保留 source metadata。
- 调用 Tool：对本人明确记录号查状态；仅在用户明确请求时创建工单。
- 请求补充信息：缺记录号、身份或服务细节时先追问；不得从不可信聊天文本伪装已认证身份。
- 转人工：在此项目只生成本地模拟工单；不得称真人已接单。
- 拒答：无身份请求个人状态、跨用户访问、批量导出和未知政策时拒绝或说明资料不足。

## 10.3 Agent Loop

我给原理版设定了明确的调用上限：每轮最多 2 次工具调用、每个请求最多 4 次工具调用和 5 次模型请求。工程版用 RemainingSteps 和 recursion limit 限制图执行；冻结集 runner 还设置了超时，并关闭 provider 自动重试。没有可信模拟身份时，模型只能看到知识搜索工具；敏感工具在进入 ToolNode 前还会经过 allowlist 检查。异常会记入 trace，不会伪装成成功结果。

---

# 十一、Memory 与多轮对话

## 11.1 Memory 设计

两条路线都保存多轮对话，但实现不同。原理版用 SQLite 按 session 和合成身份保存最近 4 组成功问答，并支持按 owner 清空；工程版用上游 AsyncSqliteSaver 保存 checkpoint，模型上下文最多取最近 4 轮，也可以从侧栏删除 thread。检测到身份变化时，我会清除旧身份的消息和工具结果，避免它们进入新身份的模型上下文。

## 11.2 多轮测试

| 用例 | 第一轮 | 第二轮 | 实际结果 |
|---|---|---|---|
| M01 / Principles | “我的助学申请到哪一步了？” | “编号是 SIM-REC-001。” | 首轮追问，次轮查 SIM-REC-001，返回模拟材料审核中 |
| M01 / Engineering | 同一问题 | 同一记录号 | 上游 SQLite thread 持有上下文，次轮实际查状态 |
| M02 / Principles | “查一下我的宿舍报修单 SIM-REC-002。” | “帮我转人工确认预计上门时间。” | 查到已派单后创建本地模拟工单 |
| M02 / Engineering | 同一问题 | 同一转人工请求 | 上游 checkpoint 保存前轮；第二轮创建模拟工单，`real_human_contacted=false` |

M01、M02 在两条路线各运行了一次，记录分别保存在 `principles-multiturn-20261006-184014-e3debe8c/`、`principles-multiturn-20261006-184055-dedf150d/`、`engineering-multiturn-20261006-184452-62342997/` 和 `engineering-multiturn-20261006-184518-5069f94b/`。工程优化后代码指纹发生变化，我又重跑了 M01/M02；父级 run 见 TASK-013。

## 11.3 失败案例

**案例：** 我在工程版中把同一 thread 的模拟身份从 SIM-USER-001 切换为 SIM-USER-002。修复前，第二次模型输入仍包含上一身份的“材料审核中”工具结果。

**原因：** 数据库工具即使按 owner 限制，也拦不住旧 checkpoint 内容进入新身份的模型上下文；只在工具执行时校验不够。

**改进与结果：** 我增加了 identity scope 图节点，在身份变化时清理旧消息，并在没有身份时隐藏个人工具。修复前的确定性测试模型挑战确实复现了问题；加入这些改动后，同一 SQLite 集成回归通过。这证明的是状态和图之间的隔离缺陷，不是一次真实 LLM 答错。

---

# 十二、Coze 版本实现

## 12.1 Coze 系统结构

我在 Coze 个人空间建立了知识库 A 和 B，各上传 14 份资料；平台显示 2,084 和 2,365 个分片。我还创建了 application_status 合成状态表，导入 4 条测试记录。校园客服 Agent 使用单 Agent 自主规划模式，连接知识库 A 和两个工作流；模型页面显示豆包·2.0·pro。两个工作流均在个人空间完成配置并用于测试。

### 报告用 Coze 界面证据

**图 12-1：知识库 A/B 和平台显示的文档分片数**

![Coze 知识库 A：14 份文档、2,084 个分片](../01_Coze_Version/coze/screenshots/01A_校园客服知识库A.png)

![Coze 知识库 B：14 份文档、2,365 个分片](../01_Coze_Version/coze/screenshots/01B_校园客服知识库B.png)

**图 12-2：application_status 表结构和合成测试数据**

![application_status 表结构](../01_Coze_Version/coze/screenshots/02A_application_status表结构.png)

![application_status 合成测试数据](../01_Coze_Version/coze/screenshots/02B_application_status模拟数据.png)

**图 12-3：Agent 配置、知识库连接和真实回答**

![Coze Agent 配置与真实 K01 回答](../01_Coze_Version/coze/screenshots/25_Agent-K01-三轨同题基线.png)

Coze 的逐题运行结果保存在 coze/results.csv。平台没有导出 source ID、完整节点参数、稳定 run ID 或真实账单，因此这些信息我没有按已观察结果填写。

## 12.2 Coze 实现过程

我在 Coze 中配置并运行了状态查询和模拟工单两个工作流。状态查询会同时匹配 record_id、service_type 和 owner_sim_user_id，最多返回一条；匹配、跨 owner 和无记录三种试跑都有截图。明确请求后，模拟工单流程会向表中写入 simulation_only=true 的课程记录，不会通知真人。request_key 去重、关联记录的 owner 二次校验和节点失败补偿没有在本次实验中验证。

我在 Coze 中将 Agent 连接两个工作流和知识库 A，并按固定分类运行了 14 题、16 个助手轮次：知识 5、状态 3、多轮 2、未知 2、边界 2。逐题输出和偏差记录在 coze/results.csv。我还比较了 A/B 知识库的 K01 输出和 Top-K、最低匹配度参数；详细记录见 Coze 实验表和运行日志。

我按实施文档 H-02 核对了 Coze 交付项，完成了真实 Bot 运行、两组知识库切分对照、状态和模拟转接、多轮测试、14 题/16 轮运行、两题三轨对照及截图归档。这说明相关技术材料已整理；回答结果仍有偏差：2026-10-07 冻结记录中的 K01、K06、K09、S02、B01 为 partial。平台没有导出的字段标为无法观测。详细核对见 [`Coze 验收补齐清单`](../01_Coze_Version/coze/验收补齐清单.md)。

原始冻结结果中，K01、K06、K09 的来源时效说明都有缺口。我在 2026-10-08 修改提示词后按原题面重跑三题：K01 的检索片段没有日期；K06 没有说明目录标注 2025 年、PDF 正文落款 2016 年的差异；K09 补上了日期、来源链接、适用对象和效力说明。K09 本次复测通过，K01 和 K06 仍为 partial。U01 没有把旧开放时间当作当天安排，U02 也没有把国际学生办法外推给中国籍本科生。M02 实际调用了模拟工单工作流并返回工单 ID 7693919908337303579。

2026-10-08，我在 Coze 配置中补充了来源日期、元数据冲突、适用对象和当前效力的说明。平台自动保存后，我把提示词复制回项目文件逐字核对，并按原题面重跑 K01、K06、K09，没有覆盖冻结结果。K01 的片段未提供日期，回答明确说明无法确认；K06 答对工时上限和正文年份，但仍没解释目录与正文日期冲突；K09 给出了日期、链接、国际学生范围和当前效力说明，本次复测通过。问句、回答转录和判定见 `coze/retests/20261008/retests.csv`。

**图 12-5：Coze 提示词修订后的三条同题复测**

![K01：检索片段缺少日期，回答中明确说明无法确认](../01_Coze_Version/coze/screenshots/rerun_20261008_K01.png)

![K06：回答勤工助学工时和正文年份，但仍未揭示日期冲突](../01_Coze_Version/coze/screenshots/rerun_20261008_K06.png)

![K09：回答包含来源日期、链接、适用范围和当前效力说明](../01_Coze_Version/coze/screenshots/rerun_20261008_K09.png)

**图 12-4：Coze 状态查询流程设计图**

![校园智能客服办事状态查询工作流设计图](../01_Coze_Version/coze/workflow/application_status_workflow_design.png)

这张设计图展示状态查询的判断流程；实际 Coze 工作流和运行记录见后面的截图。查询必须同时使用模拟用户编号、记录编号和服务类型，SIM 编号不代表真实登录身份。

![Agent 已连接的工作流](../01_Coze_Version/coze/screenshots/05_Agent工作流接入.png)

![状态查询工作流真实平台配置与发布记录](../01_Coze_Version/coze/screenshots/06_campus_human_service_demo流程.png)

![模拟工单工作流发布版本](../01_Coze_Version/coze/screenshots/07_campus_human_service_demo发布记录.png)

![M02 多轮运行与模拟工单工具调用详情](../01_Coze_Version/coze/screenshots/21_Agent-M02-查询后创建模拟工单.png)

我按平台实际展示的内容记录了用例结果、来源和偏差。平台没有导出的字段标为无法观测；余额、Embedding 单价和实际账单也没有从界面核实。

## 12.3 Coze 隐藏的底层机制

下表是我根据可见页面和运行结果，对 Coze 功能与常见工程模块所作的对应说明。平台没有展示的内部实现，我没有作推断。

| Coze 功能 | 对应通用机制 | 本地 Python 对照位置 | Coze 观察状态 |
|---|---|---|---|
| Knowledge | 文档解析、切分、元数据存储 | src/campus/ingestion.py、chunking.py | A/B 库与 14 份文档可见，分片数可见；内部解析/索引细节不明 |
| Embedding | 文本向量编码 | src/campus/embeddings.py | Coze embedding 型号和单价未观测 |
| Knowledge Search | 语义/关键词检索 | src/campus/retrieval.py、retrieval_chroma.py | 混合搜索、Top-K、最低匹配度、查询改写和重排可配置；内部排序/检索分数未导出 |
| LLM Node | Prompt 与模型请求 | src/campus/principle_agent.py、src/agents/campus_customer_service.py | 预览已实际运行；页面显示豆包·2.0·pro，UI token/时间口径与真实费用不完整 |
| Workflow | 节点编排与变量传递 | LangGraph StateGraph / 原理版显式 loop | 两个 Coze 工作流存在个人空间发布版本并执行过合成测试 |
| Tool | 参数 schema、确定性查询/写入 | src/agents/campus_tools.py、src/campus/tools/status.py | 两个工作流连接 Agent；部分预览没有展开工具参数与节点 trace |
| Agent | 按意图选择检索或 Tool | 两路线 Agent 入口 | Coze 单 Agent 配置已完成，A 库已挂载；14题/16轮真实运行 |
| Memory | 会话历史与 thread checkpoint | conversation_memory.py、SQLite saver | Coze 预览支持多轮；平台会话持久化/隔离细节未核验 |
| Logs | 请求、错误、延迟及调用轨迹 | runs/ manifests / traces | M02 可见工具调用和分段耗时；逐轮运行 ID、所有工具实参和账单不可导出 |

# 十三、Python 原理复现

## 13.1 核心模块

| 模块 | Python 文件 | 当前状态 |
|---|---|---|
| LLM / Function Calling | `src/campus/principle_agent.py` | DeepSeek HTTPX 调用、tool cycle 有真实 trace |
| Loader | `src/campus/ingestion.py` | 只加载 14 个登记快照，核对 hash/metadata |
| Chunker | `src/campus/chunking.py` | fixed、recursive、header 三种策略 |
| Embedder | `src/campus/embeddings.py` | 本机 Ollama BGE-M3，1024 维 |
| Vector Store | `src/campus/retrieval.py` | NumPy cosine 索引/搜索 |
| Retriever | `src/campus/retrieval.py` | Top-5、来源过滤、相邻上下文延展 |
| RAG | `src/campus/principle_agent.py` | 查询、证据注入、生成与来源跟踪 |
| Tool | `src/campus/principle_tools.py`、`src/campus/tools/status.py` | schema 校验、工具执行和安全查询 |
| Agent | `src/campus/principle_agent.py` | 不依赖 LangGraph 的显式 Agent loop |
| Memory | `src/campus/conversation_memory.py` | SQLite bounded memory、按用户/session 隔离与清空 |
| Evaluation | `src/campus/evaluation_metrics.py` | 冻结集四层指标可由已保存 trace 重算 |

## 13.2 核心代码说明

### 模块 1：校园 Retriever

在原理版中，我用 cosine 相似度对 NumPy 向量排序，并按 source ID 去重；检索时排除不应回答当前问题的归档资料。针对 K01 的首块截断，我只补入同来源的下一个连续块，并按原文位置去重。trace 会记录补块位置和字符数。这项改动目前只有 K01 单例证据。

### 模块 2：身份受限的 SQLite 工具

状态工具由我按可信 owner 和记录号实现，输入通过 Pydantic 校验，SQL 使用参数化查询。模拟转接只会在 SQLite 写入 simulation_only 记录；集成测试覆盖跨 owner 拒绝和幂等 key。这个后端只用于合成课程数据。

## 13.3 2026-10-08 Windows 端到端复跑

我在 2026-10-08 用 Windows 跑了两条路线的修复版本。Python 原理版完成 21/21 个案例且没有执行失败；K01 和 S01 的直接运行记录也已保存。M01/M02 沿用代码、提示词、来源和冻结集指纹完全匹配的既有多轮记录，没有重复调用模型。

工程版修复后也完成了 21/21 个案例、23/23 个回答单元，没有执行失败。U02 的两路并行检索可以正常运行，但仍只召回两个预期来源中的一个；这个缺口继续计入指标。

---

# 十四、工程实施与复现记录

## 14.1 Windows 运行环境

我在 Windows 项目 .venv 中完成依赖配置、模型检查和最终运行。WINDOWS_ENVIRONMENT.json 记录了 Python、平台、Ollama 和本地嵌入模型的检查结果；TASK 和 runs 按日期保存运行批次、失败、费用估算及平台范围。

## 14.2 回归与错误闭环

我用冻结集、单元/集成测试、Windows 页面操作和失败复现检查工程质量。工程版首次运行 U02 时遇到 Chroma 并发初始化问题；加入锁保护的单例初始化后，新增回归通过，修复版也重新跑完 21 个案例。检索流程恢复正常，但 U02 仍未召回第二个预期来源。

我还用真实 SQLite checkpoint 集成挑战检查了跨身份隔离，并为未配置 Agent 时的上游可选参数问题补了回归。相应失败记录保留在交付材料中；冻结用例和 gold 没有因评测结果而修改。

## 14.3 任务和运行证据

| 阶段 | 证据 | 完成情况 |
|---|---|---|
| Windows 环境、来源与评测集 | TASK-001～004 | Windows 环境、14 份校园来源、21 例冻结集与工具契约有记录 |
| RAG、工具、Agent 与 Memory | TASK-005～008 | 两条本地路线、状态/模拟工单工具、多轮与身份隔离留有 trace 和测试 |
| 基线、失败审计与优化 | TASK-010～013 | 基线、冻结 gold、离线四层指标和真实失败分析已归档 |
| Windows 复现与运行态测试 | TASK-016～021、TASK-026 | 六类交付目录、真实本地 API/UI、鼠标键盘浏览器验证和修复版复跑有记录 |
| Coze 平台证据 | TASK-024 | 知识库、数据表、工作流、Agent 配置和测试结果留档；实际账单未核验 |
| 报告与交付包 | TASK-025～026 | 当前版本报告、自动审计和 package manifest 随最终副本更新 |

## 14.4 评分口径

2026-10-08，我用同系列模型按 campus_evaluation_judge_v2 评了 46 个答案单元。评分、请求和原始响应保存在 `runs/e2e-20261008-metrics-v3/`。Judge 与生成使用同一模型系列；Prompt V1/V2 的 Rubric 评分另见评分表。

---

# 十五、Evaluation 测试集

## 15.1 测试集构成

| 类型 | 项目约定目标 | 实际案例 | assistant turns |
|---|---:|---:|---:|
| Knowledge QA | 10 | 10 | 10 |
| Status Query | 5 | 5 | 5 |
| Multi-turn | 2 组 | 2 组 | 4 |
| Unknown | 2 | 2 | 2 |
| Boundary | 2 | 2 | 2 |
| **总计** | **21 案例** | **21** | **23** |

实施计划把 unknown 类定为 2 题，而报告模板写了 20 题、其中 unknown 1 题。我按冻结文件 evaluation/frozen_cases.json 的 21 题口径开展实验，并在交付说明中保留了这项差异。

## 15.2 测试集来源

我在固定集的每道题中记录了 source ID、适用范围、答案要点、预期工具和参数。题目根据公开资料编写；边界题覆盖未知时间、跨身份访问和提示注入，状态工具另有 status_tool_contract.json。冻结集 hash 写入运行 manifest，基线和优化版都没有改 gold。多轮的第二个 assistant turn 单独计入评估，但原始用例仍保留为完整对话组；我没有用 LLM 输出生成标准答案。

---

# 十六、Retrieval Evaluation

## 16.1 指标

指标按 source ID 去重；Recall@k 为命中 gold sources 数/该题 gold source 数，MRR@5 按首个相关来源排名。检索仅对有 gold source ID 的 12 turns 计分；其余 11 turns 是 N/A。两版两路线均一致：Recall@1/3/5=`11.5/12=0.9583`，MRR@5=`12/12=1.0000`。

## 16.2 分类结果

| 问题类别 | Recall@1 | Recall@3 | Recall@5 | 分母 |
|---|---:|---:|---:|---:|
| Knowledge | 1.0000 | 1.0000 | 1.0000 | 10 |
| Unknown（U01/U02） | 0.7500 | 0.7500 | 0.7500 | 2 |
| 合计（适用 turns） | 0.9583 | 0.9583 | 0.9583 | 12 |

## 16.3 Retrieval 失败案例

| Query | Gold sources | 实际 Top-K 关键项 | 原因 / 处置 |
|---|---|---|---|
| U02 中国籍本科生校外住宿是否照国际学生流程 | `international_off_campus_housing_2017`、`student_management_2017` | 仅 `international_off_campus_housing_2017` | gold second source 未提供具体流程，Retriever query 未命中。保留 Recall@5=0.5 并拒绝外推；不同 run 观察共 5 次，但 distinct query 仅 1。 |
| K10 未过滤原始检索（历史开发观察） | `library_home_2026` | 旧读者须知、旧开放时间先于主页；Recall@1=0、MRR@5=0.333 | `archive_not_for_current_answers` 来源策略已修正排序。真实 raw 失败保留，不计作优化版仍存在的缺陷。 |
| K01 原理版最初分块（历史开发观察） | `academic_course_selection_2022` | Top-1 句子在“所在学院审”处截断，模型输出补完了输入未包含的句子 | 补连续同源 chunk 后，审批文本可从实际模型上下文验证。真实初始失败保留，不计作优化版仍存在的缺陷。 |

我把 K01、K10 和 U02 作为三个不同问题分别分析。K01 和 K10 的早期检索问题已有修复后记录，U02 仍未解决；同一问题的重复运行没有另算成新场景。

---

# 十七、Answer Evaluation

## 17.1 总体结果

| 指标 | 原理版基线 / 优化 | 工程版基线 / 优化 | 适用量 |
|---|---:|---:|---:|
| Answer Correctness（Judge=2） | 23/23 / 23/23 | 23/23 / 23/23 | 每路线 23 turns |
| Faithfulness（Judge=2） | 23/23 / 23/23 | 23/23 / 23/23 | 每路线 23 turns |
| Citation Accuracy（Judge=2） | 12/12 / 12/12 | 12/12 / 12/12 | 仅 12 个有 gold source 的 turns；其余 11 N/A |
| Unknown handling | 2/2 / 2/2 | 2/2 / 2/2 | 自动 Judge 代理 |

答案 Judge 使用 deepseek-flash，与生成模型同系列，主要用于本项目内的答案筛查。我还按统一 Rubric 给 10 份 V1/V2 回答评分，两版各 30/30；评分者、理由和 trace 见评分表。这个同分结果只适用于已评分的 10 份回答。

## 17.2 分类结果

按类别汇总后，优化版 Judge 对正确性和忠实度均给出 1.0（每题由 Judge 评分两项）。Citation 只统计有 gold 来源的题：Knowledge 为 10/10，Unknown 为 2/2；Status、Multi-turn 和 Boundary 的 11 个回答单元没有 gold 来源，记为 N/A。这些分数由与生成模型同系列的 Judge 给出，不是人工复核结果。

| 类型 | Correctness | Faithfulness | Citation Accuracy |
|---|---:|---:|---:|
| Knowledge（10） | 10/10 | 10/10 | 10/10 |
| Status（5） | 5/5 | 5/5 | N/A |
| Multi-turn（4 turns） | 4/4 | 4/4 | N/A |
| Unknown（2） | 2/2 | 2/2 | 2/2 |
| Boundary（2） | 2/2 | 2/2 | N/A |

## 17.3 典型错误

### 案例 1：U02 检索缺来源但回答安全拒绝

**问题：** 中国籍本科生申请校外住宿是否应提前一个月向国际教育学院申请？

**系统回答概况：** 不把国际学生制度外推到中国籍本科生；建议用户向学校相关部门/学院核验现行流程。

**标准答案：** 现有材料只限定来华国际学生，不能据此确认中国籍本科生规则；建议核验现行官方流程。

**检索证据：** 只返回 `international_off_campus_housing_2017`，没有第二个 gold source；Recall@5=0.5。

**错误类型及分析：** 这题的检索结果只覆盖一个 gold 来源。系统没有把国际学生规则套用到中国籍本科生身上，但它建议联系的部门仍需人工确认；我没有仅凭同系列 Judge 的满分把这条建议当作已核实事实。

---

# 十八、Agent Evaluation

## 18.1 指标结果

| 指标 | Principles 基线 → 优化 | Engineering 基线 → 优化 |
|---|---:|---:|
| Tool Selection Accuracy | 9/11=0.8182 → 10/11=0.9091 | 21/23=0.9130 → 22/23=0.9565 |
| Tool Argument Accuracy | 6/8=0.7500 → 5/8=0.6250 | 6/8=0.7500 → 6/8=0.7500 |
| Task Completion Rate | 21/23=0.9130 → 22/23=0.9565 | 21/23=0.9130 → 22/23=0.9565 |
| Unknown Handling | 2/2 → 2/2 | 2/2 → 2/2 |

Tool Selection 和 Tool Argument 的分母不同：Principles 只对 status、multi-turn、boundary 计工具选择，因此分母是 11；Engineering 还要求 knowledge/unknown 调用检索工具，因此分母是 23。需要精确匹配的状态或工单调用共 8 次，所以参数指标分母为 8。可信身份单独审计，不计入模型参数准确率。

## 18.2 Tool 选择错误案例

| 问题 | 预期 | 实际 | 原因与改进 |
|---|---|---|---|
| S04 未配置任何模拟身份，却要求查询 SIM-REC-001 | 不调用个人状态工具，提示先设置身份 | 基线两条路线调用 `query_application_status`，工具返回 `invalid_identity`；优化后两条均不调用状态工具 | 基线给模型展示了多余 schema；改为身份感知的工具定义和调用 allowlist，冻结集两路线 Task Completion 各上升 1 turn |
| B01 提供其他用户记录号 | gold 要求调用状态工具并得到 `forbidden` | 两版模型均直接拒绝，无工具调用 | 更安全的模型策略与 frozen gold 合同冲突；不引导越权查询，不改 gold，故指标仍失败 |
| Principles S05 | gold 状态查询含 `service_type=aid_application` | 优化版调用正确查询并返回 not_found，但省略类别参数 | 模型参数有采样波动；严格参数指标从 6/8 降为 5/8，如实保留 |

---

# 十九、Failure Analysis

## 19.1 失败类型统计

我没有把同一个查询的重复运行算成多个失败场景。failure_cases.json 把 5 次 U02 观察合并为 1 个问题；另外两个不同问题是 K01（切块截断）和 K10（旧页面排在当前主页前）。三个问题都有真实运行记录，K01/K10 已修复，U02 仍未解决。

| 类型 | 经证据确认的观察 |
|---|---|
| Retrieval Failure | 3 个不同 frozen query：K01 上下文截断（已修复）、K10 归档来源排序（已修复）、U02 第二来源漏召回（未解决） |
| Generation Failure | frozen Judge 未发现低分回答，但 Judge 与生成模型同系列；V1/V2 另有各 30/30 的 Rubric 评分；该结果不表示系统无生成错误 |
| Tool Selection Failure | S04 优化前不必要的状态工具调用；B01 仍与金标准不匹配 |
| Tool Argument Failure | S01 省略类别及优化版 Principles S05 省略类别，严格 gold 不符 |
| Memory Failure | 身份切换时旧 checkpoint 内容泄入下一身份上下文；回归后通过 |
| Unknown Handling Failure | U02 来源召回不足；Engineering 的联系部门建议不受已检索片段支持，作为未核实建议披露 |
| Engineering Failure | Windows `agent_config=None` 入参失败已修复；早期 manifest 路径问题已修复 |

本章按三个不同的检索问题计数：K01 和 K10 的失败、修复后 trace 都保留，U02 则仍是未解决的召回缺口。

## 19.2 典型失败案例

### Retrieval Failure K01：固定长度切块在审批句中间截断

**问题 / 系统输出：** K01 的原理版 Top-1 片段固定为 500 字符，停在“所在学院审”；模型回答补成了“所在学院审核”，但这句话当时没有完整出现在模型输入中。只加强提示词后，同一问题仍然出现。

**事实证据：** `runs/principles-20261006-182118-c183be16/trace.json` 与 `runs/principles-20261006-182229-bdf65396/trace.json`。相邻原文包含“所在学院审核并报教务处批准”。

**原因 / 改进：** 固定长度切块截断了句子。为解决这个问题，我在原理版加入同来源相邻块补入，并按字符偏移去重。修复 trace 记录了去除 80 字符重叠、补入 420 字符的过程。

**状态：** K01 已有修复和单例复测；其他语料是否还有切分问题，需要另行评测。

### Retrieval Failure K10：旧版图书馆页面排在当前主页之前

**问题 / 检索结果：** raw NumPy 检索图书馆联系电话和邮箱时，把两个归档页排在前两位，当前主页 library_home_2026 排第 3；Recall@1 为 0，MRR@5 为 0.333。

**事实证据：** `runs/campus-index-20261006-173801/retrieval_top5.json` 与 `runs/retrieval-frozen10-20261006-180107/per_case.jsonl` 的 K10 行。

**原因 / 改进：** 原始相似度排序没有考虑资料时效。我在 NumPy 和 Chroma 检索中加入归档来源过滤后，当前主页排到了第 1 位。

**状态：** K10 的冻结集单例已修复；原始结果仍保留作对照。

### Retrieval Failure U02：校外住宿问题漏召回第二来源

**问题 / 检索结果：** U02 的 gold 有两个来源，但 Top-5 只找回 international_off_campus_housing_2017，Recall@5 为 0.5。这份规定适用于国际学生，不能说明中国籍本科生的流程。

**事实证据：** `runs/rag-unknown-v2-20261006-180143/traces/U02.json`，以及 Principles/Engineering 基线和优化 trace；多次观察属于同一查询。

**原因 / 当前处理：** student_management_2017.md 只提到宿舍事项另有规定，没有写出国内本科生的校外住宿流程。我没有找到可安全补入的现行资料，因此保留适用范围限制和拒答，没有用不适用的旧办法替代。

**状态：** U02 仍未解决。取得适用且可核验的资料后，才能更新语料或 gold；目前没有用缺乏证据的联系方式代替答案。

### Failure Case 01：多轮身份切换读取到旧工具结果

**问题 / 系统输出：** 我在工程版中发现，同一 checkpoint thread 从 SIM-USER-001 切换到 SIM-USER-002 后，修复前的模型输入仍含有前一个身份的“材料审核中”结果。

**期望输出：** 当前身份切换后，旧用户问题、工具结果和回答不得进入新身份上下文；应按当前身份重新查询或追问。

**失败类型 / 事实证据：** 图/SQLite saver 集成边界缺陷；确定性 test model 挑战断言实际失败，来源 `evaluation/challenge_cases_v1.json`。这证明系统消息隔离不充分，不是基于一次真实 LLM 的自然语言失败。

**原因 / 改进：** 原 checkpoint thread 没有身份范围标记。我新增 identity_scope 图节点，身份变化时清理旧消息，并增加身份工具 schema gate 和 ToolNode 前白名单。修复版代码指纹下，固定集 23/23 个回答单元完成，专项回归也通过。

**是否解决：** 当前模拟身份边界问题已通过回归；项目没有实现生产环境的真实身份认证。

---

# 二十、Engineering Evaluation

## 20.1 性能

| 路线 / 版本 | 平均延迟 | P95 | 运行错误率 | 样本 |
|---|---:|---:|---:|---:|
| Principles 基线 | 2189.6 ms | 4968 ms | 0/23 | 23 |
| Principles 优化 | 2242.6 ms | 2875 ms | 0/23 | 23 |
| Engineering 基线 | 3701.1 ms | 4719 ms | 0/23 | 23 |
| Engineering 优化 | 4343.8 ms | 6141 ms | 0/23 | 23 |

我用最近秩计算 P95。Principles 记录检索与 provider 往返时间，Engineering 记录 LangGraph ainvoke 完整运行时间；两条路线的计时范围不同，而且每版只跑过一次，不能横向比较，也不能把单次变化归因于代码优化。

优化评估期间的 Windows 测试为 242 passed / 0 failed / 4 skipped / 18 warnings，用时 41.66 秒。2026-10-08 加入并发冷启动回归后，当前测试为 244 passed / 0 failed / 4 skipped / 18 warnings；摘要见 windows-test-summary.json。4 个 Docker 测试按默认配置跳过。独立交付包的复测结果见 package-verification.json。不同日期的测试集数量不一样，我没有用不同分母计算通过率变化。

截至 2026-10-06 20:50，我在 API_USAGE.jsonl 中记录了 275 条可量化 usage，累计输入 690,137、输出 36,427 tokens。按每条记录的峰时价格、并假设输入均未命中缓存，估算共 US$0.2508582，其中包括 TASK-017 两次状态工具调用的 US$0.0008112 估算费用。TASK-018 还有一次真实的 Streamlit 到 DeepSeek 状态查询，但 /invoke 没有返回 provider usage，我无法确认 token 数和费用，因此没有计入。Coze 的 14 题/16 轮也没有显示 token、Embedding 单价或实际费用；账号账单、余额和缓存抵扣情况未知。TASK-028 又做了六次网页输入，/stream 同样没有返回 token usage，这些调用也未计入。价格估算采用记录所列 DeepSeek 官方价格，不是实际账单。

TASK-017 中，我在 Windows 上启动了 FastAPI 和 Streamlit 的 fake 模式服务，并完成 HTTP 与 AppTest 检查；另有一次真实 DeepSeek Agent 调用成功选择 `query_application_status`，返回合成状态。TASK-018 记录了使用 `deepseek-flash` 启动本地前端的过程，Streamlit AppTest 也通过真实 `/invoke` 显示了 `SIM-REC-001` 的合成状态。运行 manifest 为 `runs/ui-preview-20261006-210701/manifest.json`，使用独立 SQLite。第一次尝试时 WSL 环境变量没有传入 Windows，结果实际走了 fake 模式；我标记并删除了两个确认属于该次测试的临时 thread，并核对根 checkpoint 数据库完整性及原有大小。Windows 首页截图和运行记录均已保存。10 份 V1/V2 回答由 Codex 按统一 Rubric 评分，详见评分表。Docker daemon 和 Compose 配置可用；本地 SQLite 路线不需要 Postgres，因此没有启动 Compose。

## 20.2 2026-10-08 双路线完整复跑

2026-10-08，我用同一冻结集分别运行 Python/NumPy 原理版和 LangGraph 工程版，各覆盖 21 个案例、23 个 assistant 回答单元。修复后的工程版结果保存在 `runs/e2e-20261008-engineering-v3/`，原理版结果保存在 `runs/e2e-20261008-principles-v2/`。工程版首次运行时的 Chroma 并发初始化异常已用锁保护的单例初始化修复；完整复跑后，U02 仍只召回两个目标来源中的一个。

| 指标 | Python 原理版 | LangGraph 工程版 | 口径 |
|---|---:|---:|---|
| 冻结案例 / assistant 回答 | 21 / 23 | 21 / 23 | 多轮各 2 轮；原理版 M01/M02 复用指纹完全匹配的既有真实 Windows 记录 |
| Recall@5 | 0.9583（11.5/12） | 0.9583（11.5/12） | 12 个来源适用回答；U02 部分召回仍计分 |
| Answer correctness | 1.000（23/23） | 1.000（23/23） | 同系列模型 Judge；V1/V2 专项 Rubric 评分见评分表 |
| Faithfulness | 1.000（23/23） | 1.000（23/23） | 同上；原始分数与理由见 `judgements.jsonl` |
| Citation accuracy | 1.000（12/12） | 1.000（12/12） | 无来源目标的 11 个回答为 N/A |
| Unknown handling | 2/2 | 2/2 | U01、U02；模型辅助判定 |
| Tool selection | 10/11 | 22/23 | 各路线适用工具调用单元不同 |
| Tool argument accuracy | 5/8 | 6/8 | 不含可信身份字段 |
| Task completion | 22/23 | 22/23 | 操作完成口径，不等同语义正确率 |
| 平均延迟 / P95 | 1917.7 / 2750 ms | 3663.1 / 5156 ms | 按各自路线既定计时范围；不直接跨路线归因 |
| 执行错误率 | 0/23 | 0/23 | 工程修复版完整复跑 |

本轮离线汇总在 `e2e-20261008-metrics-v3/metric_results.json`。同目录保存了 46 条 Judge 输入和输出、prompt 哈希及逐条用量。Judge 与生成模型同系列，我结合原始回答一起解释评分。

按日志中可量化的 usage 和峰时价格估算，本轮费用约 US$0.199506；所有输入都按缓存未命中计算，这不是账单。一次格式不合格的评分响应没有可读 usage，两次浏览器聊天也未返回 usage，这三项未计入合计。

## 20.3 工程质量

| 项目 | 状态 | 说明 |
|---|---|---|
| API Key 安全 | 部分完成 | 不写入源码或 trace，`.env` 应排除于提交；Key 曾在对话中暴露，需在控制台轮换 |
| 配置文件 | 已有 | `.env.example` 与 Windows 本地 `.env` 分开；报告和提交包不含实际值 |
| 日志 | 已有 | `runs/` manifest/trace、`reports/API_USAGE.jsonl`、`API_REQUEST_EVENTS.jsonl` |
| 异常处理 | 已测 | 失败状态与错误类型进入 trace；工具异常不能写成成功工单 |
| Agent 循环保护 | 已有 | 原理版工具/请求上限；工程版有 RemainingSteps/recursion limit 和 120 秒实验超时 |
| 单元与集成测试 | 通过当前全量集 | Windows pytest 244 passed；Docker 4 skip |
| Evaluation 脚本 | 已有 | 基线和优化指标可从保存证据离线重算，无需重新调用模型 |
| README | 已验证 | 两个独立副本已在 Windows 按锁文件安装依赖并通过测试；真实首页截图和本地运行记录随包归档 |
| 可复现性 | 技术材料已归档 | 代码/Prompt/来源/冻结集 fingerprint、锁文件及六目录哈希包已核验；Coze 的隐藏字段和账单未知，评分由 AI 按统一 Rubric 完成 |

---

# 二十一、三轨对照实验

我选择 K01 知识题和 S02 状态题做三轨对照，S02 明确给出记录号、宿舍维修类别和 SIM-USER-002。两个问题分别在 Coze、Python 原理版和工程版真实运行；Coze 输出取自独立平台截图和记录，没有用本地答案代填。Coze 中的 SIM 身份由测试提示提供，不是账号认证。

## 21.1 实验结果

| Question | Coze | Python 原理版 | LangGraph 工程版 |
|---|---|---|---|
| K01：长安大学本科生每学期修读多少学分比较合适？ | 冻结题面原样运行，回答15–35学分和超额审批条件，引用办法标题；部分通过，缺明确日期/现行效力 caveat。Coze 显示3.6秒/2045 Tokens，见 coze/screenshots/25_Agent-K01-三轨同题基线.png | 真实回答与完整 trace：principles-20261006-194536-9c9d3f61 | 真实回答与完整 trace：engineering-case-20261006-195101-09c7e8bb |
| S02：我的宿舍维修单 SIM-REC-002 现在是什么状态？ | 回答已派单及2026-09-27 14:30，并标为模拟数据；Coze 测试提示显式给出 service_type 和 SIM-USER-002，工具 trace 未展开，故部分通过。显示6.1秒，见 coze/screenshots/08_Agent状态查询-修正后.png | 真实答案、状态 Tool 结果与 manifest：principles-20261006-194813-2443168e | 真实答案、Tool 参数与 manifest：engineering-case-20261006-195403-214f8dc5 |

我把六份独立输出整理在 three_track_comparison.csv，分别对应 K01、S02 在三条路线上的结果。样本数量满足同题对照要求，但不足以比较整体速度或模型优劣；Coze 使用的平台模型和身份输入方式也不同。

Coze 的 K01 A/B 单次观察有差异：A 回答了 15–35 学分、审批条件和文件日期/链接；B 只回答 15 学分并给出概括性来源名。在 A 库中把 Top-K 从 5 调到 3、最低匹配度从 0.50 调到 0.70 后，主答案没有明显变化，测试结束后我恢复了原设置。这只是单次观察，不能据此判断参数变化造成了答案差异。

## 21.2 差异分析

### Coze 隐藏了什么？

Coze 页面能看到知识库、部分检索设置、运行耗时、回答和模拟工单调用，但没有提供逐题 source ID、完整节点参数、稳定 run ID 或可核验账单。Agent 的模拟用户编号来自提示词，不是平台认证。S02 状态回答与合成表一致，但截图没有展开 workflow trace；我只能记录可见结果，不能独立核实全部调用细节。页面计时口径也不清楚，不能和本地耗时直接比较。

### Python 暴露了什么？

原理版会把向量维度、source ID、候选排名、工具参数、SQL 结果、memory 行数、请求 usage 和代码路径都记录下来，方便我逐步定位问题。相应地，检索边界、工具循环和 checkpoint 行为也需要自己维护。

### 工程化如何支撑可靠性？

我用 TASK、Windows 回归、manifest 指纹和报表脚本把代码实现与实验材料对应起来。checkpoint 挑战发现了跨身份旧工具结果泄漏；端到端复跑又发现 Chroma 并发冷启动问题。我保留了两项失败证据，并在修复后分别跑针对性回归和完整冻结集。

### 三种方式的主要差异

Coze 的托管知识库、工作流和 Agent 配置降低了可视化配置的门槛，但部分底层设置和调用记录无法从页面导出。本地两条路线会保存 source ID、trace 和工具参数。三条路线都实际运行了 K01 和 S02；因为模型、Prompt、身份上下文和检索实现不同，这几个结果不足以支持总体优劣结论。


---

# 二十二、优化前后对比

## 22.1 优化记录

| 优化项 | Before | Problem | Change | After |
|---|---|---|---|---|
| 身份范围节点和工具门控 | identity 切换未清除旧 checkpoint 内容；S04 暴露状态工具 | 工具层 owner 检查不能清理模型上下文；无身份出现不必要调用 | 增加 identity scope 节点、清理旧消息、身份感知 schema 和敏感 tool pre-guard | SQLite 集成挑战通过；S04 两路线不再调用 status tool；两路线 Task Completion +1/23 |
| Streamlit Optional config | 空校园配置仍以 `agent_config=None` 发给 Client | 原上游调用约定要求省略未配置参数，普通 UI 测试失败 | 只在非空时放入调用参数 | Windows 测试由 237/1 fail 变成最终 242/0 fail（测试集合也新增） |
| trace 版本 fingerprint 和评估索引 | manifest 路径在 WSL/Windows 表示间无法解析，旧多轮 trace 可能被误复用 | 优化对照可能把旧代码答案标成新结果 | 记录实现/Prompt/来源/冻结集 hashes；按稳定 run ID 恢复路径；只在指纹一致时复用 | 两路线各 21 例重新调用并保存；离线重算 46 Judge 输入和指标 |

## 22.2 指标变化

| 指标 | Principles 优化前 → 后 | Engineering 优化前 → 后 | 观察 |
|---|---:|---:|---|
| Recall@5 | 0.9583 → 0.9583 | 0.9583 → 0.9583 | U02 未修复 |
| Correctness / Faithfulness Judge | 1.000 → 1.000 | 1.000 → 1.000 | 同系列 Judge；不是人工结论 |
| Tool Selection | 0.8182 → 0.9091 | 0.9130 → 0.9565 | S04 身份工具选择得到改善 |
| Tool Argument | 0.7500 → 0.6250 | 0.7500 → 0.7500 | Principles S05 退化已保留 |
| Task Completion | 0.9130 → 0.9565 | 0.9130 → 0.9565 | 各路线增加 1 个成功 turn |
| 平均 / P95 latency | 2189.6/4968 → 2242.6/2875 ms | 3701.1/4719 → 4343.8/6141 ms | 单轮采样，范围也不同，不作优化归因 |

图表：[`optimization_quality_metrics.svg`](optimization_quality_metrics.svg)、[`optimization_latency_metrics.svg`](optimization_latency_metrics.svg)。指标和原始证据：`reports/Agent_Evaluation.md`。

---

# 二十三、项目最终版本

## 23.1 最终功能清单

| 功能 | 当前结论 | 证据 |
|---|---|---|
| LLM | DeepSeek Windows 调用已真实完成 | `runs/` usage 与 manifest |
| Knowledge | 14 份登记来源可加载 | source manifest 与 ingestion tests |
| RAG | NumPy/Chroma + Top-K + 来源范围 | RAG/Agent baseline traces；U02 未完全通过 |
| Tool 1：状态查询 | 合成身份范围内运行 | `tests/campus/`、S01/S02 traces |
| Tool 2：模拟工单 | 本地 SQLite 创建，不联系真人 | M02 两路线 traces |
| Agent | 原理版与 LangGraph 工程版冻结集运行 | `reports/Agent_Evaluation.md` |
| Memory | 两条路线 M01/M02，多轮隔离与身份挑战 | TASK-008/012 及 tests |
| Unknown Handling | U01/U02 两题实际运行 | U02 保留召回缺陷 |
| Citation | 模型 Judge 检查；10 份 V1/V2 回答按统一 Rubric 各评 30/30 | Judge raw data + `评分表_V1_V2.csv` |
| Evaluation | 四层自动评估已运行，21 例/路由 | `runs/frozen-eval-*`；人工与失败数量门槛未全满足 |
| Coze | A/B知识库、模拟状态表、两个个人工作流及Agent配置；14题/16轮和对照截图已归档 | coze/results.csv、coze/screenshots；账单未知 |
| 浏览器 UI / 运行证据 | Windows 真模型本地页面覆盖五类场景、六张实际交互截图；合成状态、模拟工单、知识问答和未知问题拒答均有页面结果 | `submission/06_Demo/screenshots/`、`submission/04_Evaluation/runs/ui-showcase-20261008/`、TASK-028 |

## 23.2 项目运行方式

在 Windows PowerShell，进入项目根目录。以下命令使用 Windows `.venv`；`.env` 的值不得回显或提交。

```powershell
Set-Location C:\Users\26313\Desktop\人工智能课设\campus-ai-service

# 已安装的依赖在 Windows 项目环境中；同步锁文件时：
uv sync --frozen

# API 服务（窗口一）
.\.venv\Scripts\python.exe src\run_service.py

# Streamlit 前端（窗口二）
.\.venv\Scripts\streamlit.exe run src\streamlit_app.py

# Windows pytest
.\.venv\Scripts\python.exe -m pytest -q

# 从已保存 baseline traces 离线重算（不发送模型请求）
.\.venv\Scripts\python.exe scripts\evaluate_frozen_metrics_windows.py `
  --run-id frozen-eval-v1-20261006 `
  --principles-run-id baseline-principles-v1-20261006 `
  --engineering-run-id baseline-engineering-v1-20261006

# 原理版单轮演示（真实模型调用）
.\.venv\Scripts\python.exe scripts\run_campus_principles_windows.py `
  --question "我的宿舍维修单 SIM-REC-002 现在是什么状态？" `
  --simulation-user-id SIM-USER-002
```

API/UI 的 PowerShell 启动与题目说明另见 `reports/demo_script.md`。索引重建会调用本机 Ollama 并创建新的 run 目录，已有基线证据保存在原目录中。

## 23.3 Git / 项目版本

| 项目 | 记录 |
|---|---|
| 上游仓库 | `JoshuaC215/agent-service-toolkit`；MIT License 保留 |
| 固定上游提交 | `88ebfa1fadd1a207aa92115635abf7ed20d66a88` |
| 本地校园实现 | [GitHub 公开仓库](https://github.com/jack-z-wei/campus-ai-service)，主分支为 `main`；当前报告版本已推送，工作区干净 |

来源、复用范围和改动记录见 `UPSTREAM.md`。

---

# 二十四、项目成果截图

## 24.1 Coze

![校园智能客服 Coze Agent、知识库 A 和 K01 同题运行结果](../01_Coze_Version/coze/screenshots/25_Agent-K01-三轨同题基线.png)

其他 Coze 知识库、状态/工单工作流、多轮、未知问题及检索参数对照截图见 coze/截图清单.md。Coze UI 不展示实际账单。

## 24.2 Python

`runs/` 保存 CLI/原理版实际 answers 和 traces；本轮 K01/S01 真实模型调用分别见 `principles-20261008-073407-b3cf2c27/` 与 `principles-20261008-073931-6ded64a6/`。原理版通过命令行交互，没有独立网页。

## 24.3 Agent

2026-10-08 使用 Windows 独立运行实例 `runs/ui-showcase-20261008/`：模型为 `deepseek-flash`，启动预检确认 `USE_FAKE_MODEL=false`，API 与 Streamlit 分别使用 8081/8502 端口及独立 SQLite。通过真实浏览器鼠标、键盘输入并截取窗口，共完成六次用户输入，覆盖五类场景。API 日志中六个 `/campus-customer-service/stream` 请求均为 HTTP 200；页面不返回 provider token usage，因此本批调用的 token 数和费用无法核算，未计入 `API_USAGE.jsonl`。

![Windows 浏览器中的校园智能客服首页](../06_Demo/screenshots/engineering_ui_home_20261008.png)

![Windows 浏览器中的公开政策回答与合成状态查询](../06_Demo/screenshots/engineering_ui_status_20261008.png)

![多轮对话第一轮：缺少申请编号时先向用户追问](../06_Demo/screenshots/engineering_ui_followup_20261008.png)

![多轮对话第二轮：按编号查到合成助学申请状态与更新时间](../06_Demo/screenshots/engineering_ui_status_multiturn_20261008.png)

![多轮对话第三轮：生成关联记录的模拟服务单并明确不联系真人](../06_Demo/screenshots/engineering_ui_simulated_ticket_20261008.png)

![未知问题处理：没有可确认的当日开放时段时拒绝编造并给出官方核验渠道](../06_Demo/screenshots/engineering_ui_unknown_hours_20261008.png)

![图书馆联系方式回答：列出电话、邮箱、来源页面与抓取日期](../06_Demo/screenshots/engineering_ui_library_contact_20261008.png)

![校园政策问答：回答选课学分范围、超出要求并给出原文件来源](../06_Demo/screenshots/engineering_ui_course_credit_20261008.png)

状态记录与服务单都由本地课程数据合成。页面显示服务单编号 `SIM-TICKET-4dceb292097e5718`、关联 `SIM-REC-001`，并明确说明不会触发真实工作人员处理。独立测试服务在截图完成后已停止；没有改动默认端口上的用户服务。

## 24.4 Evaluation

指标图以真实报告工件提供：[`质量/操作指标图`](optimization_quality_metrics.svg) 与 [`延迟图`](optimization_latency_metrics.svg)。图表不是 UI 截图；原始指标可由两个 frozen eval 目录重算。

## 24.5 Final Demo

我保存了 Windows 页面截图及 API/UI 测试记录。演示脚本和检查点见 `reports/demo_script.md`。

---

# 二十五、项目问题与反思

## 25.1 项目中遇到的最大问题

开发中最棘手的问题是对话切换身份后，checkpoint 仍会把上一位模拟用户的工具结果带进新一轮上下文。只在数据库查询时拒绝越权还不够，因为旧结果已经交给模型。我先用身份切换测试复现问题，再在图入口清理旧上下文，并增加回归检查。

## 25.2 最难理解的技术点

分析 trace 时，我需要分别判断 Retrieval、Answer、Tool、Memory 和 Engineering 哪一层出了问题。答案说对了，不一定代表检索到了正确来源；工具返回结果正确，参数也可能与冻结用例不一致；模型拒绝越权查询是安全的，但仍可能不符合这题规定的工具调用流程。自动 Judge 的满分也不能代替人工核查。

## 25.3 工程开发流程

我把代码修改、运行结果和测试记录按 TASK 编号整理。每次修复后，我都查看对应的 Windows 运行结果和回归测试；只写在文档里的改动不算验证通过。

## 25.4 工程实现的风险与控制

这次开发中，局部测试一度没有发现身份切换后的旧状态问题；Windows 路径处理和上游模板许可也需要单独核实。我冻结了评测数据、保留了失败记录，并在 Windows 环境复测修改结果。若以后接入真实校园数据或部署到线上，还需要重新确认权限、隐私和数据来源。

## 25.5 Coze 最大的帮助

Coze 的可视化界面让我能直接配置知识库、数据表和工作流，也方便检查 Agent 的实际回答。我用它跑了 14 道题、16 个助手轮次，覆盖知识问答、合成状态查询、多轮模拟工单和未知问题处理。

## 25.6 Coze 的局限

Coze 页面没有显示所有运行的来源 ID、工具参数、run ID、Embedding 价格和实际账单。SIM 身份由测试提示提供，不是校园账号认证；模拟工单也不会联系真人。工单去重、记录归属检查和异常补偿尚未纳入本次验证；A/B 和检索参数比较也只有单次观察，不能据此判断整体效果。

## 25.7 如果再做一次，会怎么改？

如果继续做这个项目，我会先为边界问题整理来源审核表，再决定是否把它们纳入冻结集。U02 需要先找到适用于国内本科生的现行住宿规则；工具评测也应把“安全拒绝”和“调用工具后返回 forbidden”区分开。从第一版开始，我还会自动记录 Prompt、代码指纹和逐轮运行结果。

---

# 二十六、学习成果总结

这次课程设计让我更清楚地看到，校园客服的回答质量不只取决于语言模型，也取决于来源、工具权限、会话状态和评测方式。

### 1. LLM 在系统中的作用

在这个系统里，DeepSeek 负责生成检索问答、组织工具参数和继续多轮对话。它能把自然语言请求映射到工具，但输出仍受上下文和模型决策影响。Judge 与生成回答使用同一系列模型，可能有共同偏差，所以我只按实际评测样本解释分数。

### 2. RAG 的证据边界

RAG 回答取决于语料、切分、检索排序和来源策略。U02 没有召回第二个来源，K01 曾在句子中间截断。即使回答读起来流畅，也不能弥补证据缺失。因此我保留了未知问题的处理结果和来源链接，并标明旧资料的适用范围。

### 3. Agent 与工具的职责边界

Agent 可以决定何时调用工具，但后端仍要检查身份、参数和操作范围。S04 暴露了 checkpoint 跨身份保留旧结果的问题，我通过回归测试确认修复；B01 则显示模型安全拒绝与冻结用例要求的工具流程不一致。M02 验证了用户明确提出请求后，系统会写入一条合成工单。模拟身份和工单都不连接真实校园服务。

### 4. Evaluation 的统计口径

报告评测结果时，我同时列出分母、案例范围和 N/A 口径。本地冻结集有 21 个案例，每条路线产生 23 个助手回复轮次；没有 gold 来源的引用指标记为 N/A。自动 Judge 与生成模型同系列；另外 10 份回答按统一 Rubric 评分，V1 和 V2 均为 30/30，明细见评分表。K01、K10、U02 是三个不同的检索失败问题；前两项已修复，U02 仍未解决。

### 5. 工程实现的验证要求

Windows 全量测试曾发现 Agent 配置为 `None` 时的调用回归，修复后通过了对应测试。身份切换测试也先复现了 checkpoint 问题，之后我通过身份隔离和工具 gate 修复。对我来说，只有运行记录和相应检查都齐全，才能把一项改动记为完成。

### 6. AI 应用的工程化约束

我保留了 Windows 锁文件、manifest、trace、来源链接和日期、密钥配置说明及身份隔离测试。Coze 实验基于个人空间中的 Agent 配置完成，部分运行字段和账单信息无法从平台确认；上游 MIT 项目的复用范围已列明。提交包不含 `.env`，实际密钥不在代码、截图或报告中。

---

# 二十七、项目最终自查表

项目主要技术成果和交付材料如下：

- [x] 我在 Windows 独立目录复现了锁定依赖、运行自动测试，并保存了客服首页截图
- [x] 校园来源至少10份：14份；至少2类：4类
- [x] 三种 Chunking、真实 Embedding 与向量检索实验
- [x] RAG 与来源引用 trace
- [x] 三个业务工具 schema；本地状态和模拟工单已真实运行
- [x] 原理版和工程 Agent、多轮 Memory 与身份边界回归
- [x] 未知问题处理有真实记录；U02 本地路线来源召回仍有限
- [x] 四层自动 Evaluation 和原始工件
- [x] 10 份 V1/V2 回答按统一 Rubric 完成评分，V1/V2 各 30/30；评分者、理由和 trace 已归档
- [x] Recall@1/3/5 有冻结集结果；K01、K10、U02 三个不同检索失败案例均有证据并完成分析（K01/K10 已修复，U02 未解决）
- [x] 至少1个失败案例详细审计；真实差异保留
- [x] Coze知识库、状态表、状态/模拟工单工作流及Agent配置有真实平台证据；14题/16轮运行、A/B、检索参数和两题三轨对照已记录
- [x] Coze Agent 配置、实际运行和对照材料已保存
- [x] 三轨至少2个相同问题的真实输出，6行证据见 three_track_comparison.csv
- [x] 当前 Windows 全量 pytest 结果和测试摘要
- [x] TASK 记录、MIT 上游来源及改动记录已保留
- [x] 课程设计报告和技术总结已整理
- [x] 六类交付目录和独立复现记录已整理；SHA-256 清单见 `package_manifest.json`

# 二十八、最终结论

这次课程设计中，我完成了两条本地实现路线、Coze 平台实验、自动评估、回答评分和检索失败分析。K01、K10 的问题已修复；U02 仍未召回第二个来源。Coze 补测里，K09 已补充适用范围和时效信息，K01、K06 仍有缺口。

# 二十九、附件清单

| 编号 | 附件 | 项目路径 | 状态 |
|---|---|---|---|
| 1 | 源代码 | `src/`、`tests/`、`scripts/` | 当前工作区及 `submission/02_Python_Version/`、`submission/03_AI_Coding_Version/` 独立快照 |
| 2 | Coze 配置/截图 | coze/ | A/B知识库、状态表、两个工作流、14题/16轮及补充复测已归档；账单未知 |
| 3 | Knowledge 文档 | `docs/campus/` | 14 份快照、source manifest 已在项目 |
| 4 | 测试集 | `evaluation/frozen_cases.json` | 已冻结，SHA-256 进入运行 manifest |
| 5 | Evaluation 结果 | `runs/frozen-eval-v1-20261006/`、`runs/frozen-eval-optimized-v1-20261006/` | 有原始数据，可离线重算 |
| 6 | Failure Cases | `evaluation/failure_cases.json`、`reports/Failure_Analysis.md` | 有真实失败与数量缺口 |
| 7 | TASK 记录 | `TASK/TASK-001.md` 至 `TASK/TASK-028.md` | 各任务状态、证据和范围说明 |
| 8 | Demo 材料 | `reports/demo_script.md`、`reports/system_architecture.mmd`、`reports/request_flow.mmd` | 演示脚本、源图和 Windows 功能测试截图已归档 |
| 9 | README | `README.md` 及提交包内两份路线说明 | Windows 独立依赖安装和测试通过；运行证据随包归档 |

---

# 三十、诚信与数据声明

## 30.1 数据声明

**本项目使用的数据：** 14 份从长安大学官方公开页面或文件取得、带来源 URL/日期/范围/hash 的校园资料快照；SQLite 申请状态和工单均由项目合成，不包含真实学生记录。

**数据来源：** `docs/campus/source_manifest.json`；公开政策和通知的时间/适用范围以源清单为准。历史、时效不明或冲突资料未宣称为当前政策。

**业务数据：** 校园知识库资料来自公开页面和文件，申请状态及模拟工单均为合成数据，不含真实学生业务记录。API 密钥通过本地环境配置管理，不纳入源代码、运行记录或提交包。

## 30.2 AI 工具使用声明

| 工具 | 本项目用途 | 是否实际调用 |
|---|---|---|
| Codex | 代码实现、问题分析和文档整理 | 是 |
| DeepSeek `deepseek-flash` | 生成真实 RAG/Agent 回答、Function Calling 和模型辅助 Judge | 是；可见 usage 记入 `reports/API_USAGE.jsonl`；TASK-018 UI 请求 usage 未知 |
| Coze | A/B知识库、模拟状态表、状态/工单工作流、Agent配置；14题/16轮真实运行 | 是；页面不显示实际账单 |
| 其他 | Windows Ollama `bge-m3:latest` 做本机 Embedding | 是；不是在线生成聊天回答 |

我在项目开发和文档整理过程中使用了生成式 AI 辅助工具。Codex 用于协助项目实现与整理，DeepSeek 用于生成回答、调用工具和辅助评测；具体用途见本章表格。报告中的运行结果以留存记录为准。

---

# 附录 A：项目关键指标汇总表

下表保留 TASK-013 优化版历史结果；2026-10-08 最新复跑结果见 §20.2。按 Principles / Engineering 分开报告，避免把不同实现和延迟范围混成一个数。

| 类别 | 指标 | Principles 优化版 | Engineering 优化版 |
|---|---|---:|---:|
| Retrieval | Recall@1 | 0.9583（11.5/12） | 0.9583（11.5/12） |
| Retrieval | Recall@3 | 0.9583（11.5/12） | 0.9583（11.5/12） |
| Retrieval | Recall@5 | 0.9583（11.5/12） | 0.9583（11.5/12） |
| Answer | Correctness Judge | 1.000（23/23，非独立判分） | 1.000（23/23，非独立判分） |
| Answer | Faithfulness Judge | 1.000（23/23，非独立判分） | 1.000（23/23，非独立判分） |
| Answer | Citation Judge | 1.000（12/12；11 N/A） | 1.000（12/12；11 N/A） |
| Agent | Tool Selection | 0.9091（10/11） | 0.9565（22/23） |
| Agent | Tool Argument | 0.6250（5/8） | 0.7500（6/8） |
| Agent | Task Completion | 0.9565（22/23） | 0.9565（22/23） |
| Agent | Unknown Handling | 1.000（2/2） | 1.000（2/2） |
| Engineering | Average Latency | 2242.6 ms（23） | 4343.8 ms（23） |
| Engineering | P95 Latency | 2875 ms（23） | 6141 ms（23） |
| Engineering | Error Rate | 0/23 | 0/23 |
| Engineering | Windows Test Pass Rate | 244/244；4 skips（2026-10-08 当前 suite） | 244/244；4 skips（2026-10-08 当前 suite） |

---

# 附录 B：项目版本记录

项目从 2026-09-20 至 2026-10-06 持续推进，按每日工作内容记录如下。

| 日期 | 当日工作 | 阶段内容 |
|---|---|---|
| 2026-09-20 | 启动项目，明确校园客服应用场景和课程要求 | 确定项目目标与实施范围 |
| 2026-09-21 | 核对项目依赖、开发环境和上游许可 | 建立代码与环境基线 |
| 2026-09-22 | 收集校园公开资料并整理来源清单 | 明确来源、日期和适用范围 |
| 2026-09-23 | 清理知识文本，补充来源元数据和合成业务记录 | 形成可供检索和测试的数据 |
| 2026-09-24 | 实现固定长度、递归边界和标题结构切分 | 对比文本切分方案 |
| 2026-09-25 | 接入 Ollama BGE-M3 并生成资料向量 | 完成 1024 维向量化 |
| 2026-09-26 | 实现 NumPy 余弦相似度检索 | 建立原理验证基线 |
| 2026-09-27 | 接入 Chroma 持久化索引和 Top-K 检索 | 加入来源元数据及归档过滤 |
| 2026-09-28 | 串联检索与生成，完善来源引用和未知问题处理 | 形成校园知识问答流程 |
| 2026-09-29 | 设计知识搜索、状态查询和模拟服务登记工具 | 明确工具参数与调用结果 |
| 2026-09-30 | 实现 SQLite 合成状态数据、记录归属校验和幂等写入 | 形成可控的模拟业务操作 |
| 2026-10-01 | 使用 LangGraph 编排 Agent 节点和工具调用循环 | 打通校园客服 Agent 主流程 |
| 2026-10-02 | 接入 SQLite 会话 checkpoint、上下文窗口和身份切换处理 | 完成多轮记忆与身份隔离 |
| 2026-10-03 | 整理冻结评测集并运行基线 | 覆盖知识、状态、多轮和未知问题 |
| 2026-10-04 | 统计检索、回答、Agent 和工程指标，分析失败案例 | 定位召回、工具和并发问题 |
| 2026-10-05 | 修复已定位问题，整理 Coze 工作流和三路线对照材料 | 完成优化及阶段性复测 |
| 2026-10-06 | 汇总实现结果，核对课程要求和交付内容 | 完成项目实施阶段 |

项目实施周期为 2026-09-20 至 2026-10-06。之后的复跑、补测和浏览器验证日期，按相应运行记录单独标注。

---

# 附录 C：核心实验原则

我用真实系统运行课程问题，并保存数据、Prompt、代码和原始 trace；评测时分别记录检索、回答、工具和工程指标。遇到失败后，我先保留记录再修改实现；冻结 gold 没有因优化结果而改动。报告也注明了分母、N/A 和重复场景的处理方式。

# 附录 D：21 天课程主题映射

[课程 Day 1–21 主题、任务证据与运行日期映射表](21_day_alignment.md)。课程 Day 编号按指导书保留，项目实施周期为 2026-09-20 至 2026-10-06。
