# Coze、Python 原理版与 AI 工程版模块映射

截至 2026-10-08，我已按实施文档 H-02 整理 Coze 的平台配置、分类用例和对照材料。这里说的“完成”是指材料和运行记录已经归档；实际回答中仍有 partial 结果，教师验收状态也没有记录。逐题输出、偏差和截图位置见 `coze/results.csv`、`coze/logs/agent-evaluation-20261007.md` 和 `coze/截图清单.md`。

2026-10-08，我在 Coze 草稿中补充了来源日期和效力说明，并把平台提示词复制回项目文件逐字核对。原冻结集结果没有改动。三条同题复测单独保存在 `coze/retests/20261008/retests.csv`：K09 补上了 2017 年日期、来源链接、适用对象和当前效力说明；K01 说明检索片段没有日期；K06 仍未说明目录日期与正文日期的差异，后两题继续判为 partial。提示词和复测截图也已归档。

## 三条路线的模块映射

| 能力 | Coze 实际配置与结果 | Python 原理版 | AI 工程版 | 可确认的差异与限制 |
|---|---|---|---|---|
| 校园知识来源 | `coze/knowledge/` 与 `source_manifest.csv`；A/B 各 14 份来源快照 | `src/campus/ingestion.py`、`knowledge.py` | 同一来源快照，经本地 RAG 组件加载 | Coze 页面可见文档与分片数；平台未导出全部来源 ID 与逐轮引用元数据 |
| 文本切分 | `coze/experiment_sheet.csv`；A 为 500 字符、双换行、16% 重叠，2,084 片；B 为 700 字符、单换行、0% 重叠，2,365 片；K01 在 A/B 各有真实输出 | `src/campus/chunking.py` 的 fixed、recursive、header 策略 | 共用项目切分结果；Chroma RAG 检索 | 两组平台配置和 K01 输出均留证；单题单次观察只作定性比较，不作统计因果结论 |
| Embedding 与向量检索 | Coze A 库：自动调用、混合检索、Top-K 5、最低匹配度 0.50、查询改写和重排开启；K01 另试 Top-K 3、阈值 0.70 后恢复基线 | `src/campus/embeddings.py`、`src/campus/retrieval.py`（本机 BGE-M3 与 NumPy cosine） | `src/campus/retrieval_chroma.py`（本地 Chroma 路线） | Coze embedding 型号、向量维度、内部排序分数、单价和实际账单不可见；不得与本地耗时或成本作未经校准的排名 |
| 知识问答与来源 | 单 Agent 草稿连接知识库 A；14 个原冻结用例见 `coze/results.csv`；修订提示词后的 K01/K06/K09 补充复测见 `coze/retests/20261008/retests.csv` | `src/campus/principle_agent.py`、`prompts/campus_system_v1.md` | `src/agents/campus_customer_service.py`、同一来源体系 | 冻结记录未覆盖。补测 K09 已补足来源/范围/时效说明；K01 缺少检索日期，K06 未披露元数据日期冲突，仍为 partial |
| 模拟状态查询 | `campus_service_status_query`（ID `7693891212118818854`）；按 `record_id`、`service_type`、`owner_sim_user_id` 同时匹配、最多一条；匹配、跨 owner、无记录直接试跑有截图 | `src/campus/principle_tools.py`、`src/campus/tools/status.py` | `src/agents/campus_tools.py` 与 LangGraph 状态节点 | Coze Agent 的 SIM 编号来自合成测试输入，不是登录认证；S02 结果可见但逐轮 workflow arguments/trace 未完整导出 |
| 模拟人工转接 | `campus_human_service_demo`（ID `7693901471003689023`）；直接试跑与 M02 Agent 调用分别产生可见合成记录 | 原理版工具写入本地 SQLite | 工程版工具写入本地 SQLite | Coze 只作 `simulation_only` 演示，不通知真人；本次未验证 request_key 去重、关联记录归属检查或失败补偿 |
| 多轮记忆 | M01 追问必要字段后查询；M02 查询状态后，在明确请求下创建模拟工单 | `src/campus/conversation_memory.py` | 上游 SQLite checkpointer 与 Agent 状态管理 | Coze 预览真实完成两组对话；平台会话持久化、认证身份绑定和隔离机制未核验 |
| 未知与边界 | U01/U02、B01/B02 均有真实回复；逐项状态见 `coze/results.csv` | 两条本地路线按冻结集运行并保存 trace | 同左 | B01 可见拒绝答复但缺少可展开的 workflow trace，不能把回复截图描述成已证明“未调用工具” |
| 评测与运行证据 | 21 个冻结用例中选取 14 题、共 16 个助手轮次真实运行；14 行含实际答案，7 行保留为空表示本次 Coze 未运行；A/B、检索参数和两题三轨对照均有独立记录 | `runs/principles-*/manifest.json`、`trace.json` | `runs/engineering-*/manifest.json`、`traces/turn_*.json` | Coze 部分字段由平台隐藏，统一标为无法观测；平台运行不等于公开发布或教师签收 |

## 指导书 Coze 交付项核对（H-02）

| 指导书要求 | 当前证据 | 结论 |
|---|---|---|
| 建立并运行真实 Bot，保留至少 5 个校园问题的早期结果 | Agent 配置/早期 K01 截图 03；K01、K05、K06、K09、K10 的真实回答截图 09–13 | 已运行并归档 |
| 知识检索、来源回答、未知处理、状态和转接工具、至少两组多轮 | 知识、状态、未知、边界、多轮用例；两个已发布个人空间 Workflow；M01/M02 | 已运行并归档；身份与模拟工单范围已说明 |
| 至少两组实际切分设置及同题输出 | `coze/experiment_sheet.csv` 的 A/B 设置、K01 实答与截图 09、22 | 已完成；单次比较不宣称统计显著 |
| 至少 10 个固定用例并保存可观察运行信息 | `coze/results.csv` 有 14 条平台实答、16 个助手轮次及截图/偏差 | 数量已满足；5 条为 partial，7 个冻结用例未在 Coze 执行，未填假答案 |
| 与两个本地版本各运行同一知识题及带明确参数的状态题 | K01、S02 在三条路线各一份实际输出，`reports/three_track_comparison.csv` 共 6 行 | 已完成；路线身份上下文和计时口径差异已注明 |
| 保存配置、工作流、日志；不暴露的字段标记无法观测 | `coze/screenshots/`、工作流设计/合同、实测 CSV/日志和截图索引 | 已归档；source ID、部分工具参数、稳定 run ID、账单不可见 |

按 H-02 的技术清单，Coze 配置、运行数量和截图材料已经整理齐全。原始回答中的偏差和平台没有展示的字段仍按实际情况记录。Agent 目前是未公开草稿；我没有把这些材料写成教师已验收。

文中提到的原始 14 题、16 轮和 5 条 partial，均指 `results.csv` 中 2026-10-07 的冻结记录。2026-10-08 另跑了 3 题，1 题通过、2 题仍为 partial；这三条复测没有覆盖旧结果，也不计入原始数量。
