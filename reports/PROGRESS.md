# 项目进度

更新时间：2026-10-08（Asia/Shanghai）。我完成了工程版真模型网页展示测试，并归档了截图。

## 当前状态

- 当前阶段：工程版真实网页交互展示补测与截图归档已完成。
- 当前任务：TASK-028 已完成。Windows 独立 `deepseek-flash` 真模型页面完成六次用户输入，覆盖多轮助学状态查询、模拟工单、图书馆当日开放时间拒答、图书馆联系方式来源和选课学分政策五类场景；六张实际浏览器截图已插入最终报告。API 日志中六个 `/stream` 请求均为 HTTP 200。此接口不回传 token usage，成本未知且未计入 API_USAGE；独立测试服务截图后停止。
- 最新完成：TASK-028 六张 Windows 真模型网页截图、运行记录和六条输入已归档；两份最终报告、演示脚本、审计记录和截图索引已更新。Windows 提交包 manifest 已刷新为 6 目录、1,628 个内容文件；最终报告 40 个本地链接均已解析。原 TASK-027 的 Coze Agent 草稿仍未公开发布，教师签收和平台账单均未声称完成。
- 最近完成：Coze 个人空间状态/模拟工单工作流均有发布版本及真实合成执行；Agent连接两者和A库。保存14题/16助手轮次。三轨6行输出齐全；Coze的K01/S02为实际页面输出，并注明提示中的SIM身份不是认证。报告Coze章节、验收记录、截图清单和manifest已更新。
- 初始化时，我手头只有课程资料，没有可继续使用的项目代码。之后我按固定提交初始化工程版；后面的 TASK 记录按发生顺序保存了项目进度。

## 已完成

以下历史任务记录保留完成当时的状态；较早条目中的个人信息、现场演示和教师许可是当时的状态快照。当前项目范围决议和报告处理见 TASK-025，不将范围排除写成已发生或已验收。

- TASK-023：按校园合成状态表制作办事状态查询流程设计图，含三项 AND 条件、受控合成身份、结果判断和返回分支。Windows Edge 导出 1680×1040 PNG，SVG / Mermaid 源图同步保留，已插入报告 12.2 图 12-4；未产生新的 Coze 实测结果或模型调用。

- TASK-027：复核 Coze 交付对照《两天实施计划》H-02，修订提示词及过时映射，完成 K01/K06/K09 三条同题平台补测（1 pass、2 partial），原始14题/16轮结果不覆盖。Windows 提交包 6 目录/1,614 文件 SHA-256 已核验；Coze 34 张截图已归档，报告链接34个且失效0个；实际账单、平台隐藏字段和教师签收状态如实保留。

- TASK-028：在 Windows 独立端口 8081/8502、独立 SQLite 与 `USE_FAKE_MODEL=false` 的 `deepseek-flash` 配置下，通过真实浏览器鼠标键盘进行六次输入并截取页面。覆盖缺编号追问、助学合成状态、关联模拟工单、图书馆当日开放时间未知拒答、官方联系方式引用、选课学分政策引用。六个 Stream 请求均返回 HTTP 200；截图已插入两份最终报告并复制至 `submission/06_Demo/screenshots/`，场景输入和运行 manifest 归档至 `submission/04_Evaluation/runs/ui-showcase-20261008/`。模型 usage 不可见，不估算该批费用。

- TASK-021：校园客服界面和工程 README 已改；只保留校园 Agent、演示身份、中文服务范围与本地记录操作。原 MIT LICENSE 和 `UPSTREAM.md` 来源披露保留。更新 `campus-ai-service` 项目元数据与 Windows lock 根包名，提交 README、工程元数据与界面已使用校园品牌表达，同时保留明确来源记录和原许可。V1/V2 评分表逐行附 30 项判断理由。

- TASK-010 基线与 TASK-013 优化版均在 Windows 项目 `.venv` 完成双路线 21 个冻结用例（每路线 23 个 assistant turn），每版 46 条回答 Judge 全部完成。指标可从各自 runs 原始 trace、unit、judgement 与 `metric_results.json` 离线重算；答案 Judge 使用与生成同系列模型。
- 冻结集优化对照：U02 Recall@5 仍 0.9583（单题依然 0.5）；Tool Selection Principles 9/11→10/11、Engineering 21/23→22/23；Task Completion 两路线 21/23→22/23；Principles Tool Argument 6/8→5/8 的 S05 参数遗漏退化已记录。未知处理 2/2。延迟范围不同，详见 `reports/Agent_Evaluation.md`。
- TASK-011 已交付 `evaluation/failure_cases.json` 和更新后的 `reports/Failure_Analysis.md`。U02 有三份运行观察，但只有一个不同失败查询；“三种独立检索失败场景”仍未达到，不以重复计数凑验收。
- 身份切换多轮挑战发现真实上下文隔离缺陷：同一 checkpoint thread 从 SIM-USER-001 切换至 SIM-USER-002 后，上一身份的模拟状态结果进入下一次模型输入。已加图级身份范围清理、无身份工具门控及回归用例；修复前测试 1 failed，修复后定向相关测试 `20 passed`。
- 上游复用核查补充在 `UPSTREAM.md`：沿用原 Streamlit 对空可选 `agent_config` 的省略约定；上游 LangSmith 单星反馈不是冻结四层评估器；其通用 RAG 未解决 U02 的校园来源缺口。
- 已知 API usage 快照（截至 2026-10-06 20:50）：275 条可量化记录，输入 690,137、输出 36,427 tokens；逐次估算合计 US$0.2508582（峰时、假设输入缓存未命中），其中包括 TASK-017 两次模型 invocation（估算 US$0.0008112）。TASK-018 另有一条成功的 DeepSeek UI 请求，但 `/invoke` 未返回 token usage，调用次数与费用未知且未计入 275 条。以上不是实际账单；Coze 请求 0。Windows 项目全量测试为 242 passed / 0 failed / 4 skipped / 18 warnings，41.66 秒；两个独立交付环境也按锁安装并测试通过。

- 已阅读本目录《两天实施计划.md》《课设要求解读与验收清单.md》《GitHub基础项目选型.md》、实验指导书 V3.2 和报告模板 V1.0。工作目录及上级目录未发现额外 `AGENTS.md`；本次遵循用户提供的全局指导。
- 查明原课程清单仅是实施计划，尚无项目代码、评测或实验结果。
- 在 Windows 文件系统下克隆上游 `JoshuaC215/agent-service-toolkit`，固定提交 `88ebfa1fadd1a207aa92115635abf7ed20d66a88`；上游 MIT 许可已保留。
- Windows Python 可执行文件存在于 `C:\ProgramData\anaconda3\python.exe`，版本为 3.12.7；Windows Git、uv 和 Ollama 可执行文件已定位。
- Ollama `127.0.0.1:11434` 当前可访问，模型清单包含 `bge-m3:latest`；Windows 实际 `/api/embed` 对中文输入返回 1 条、1024 维有限数值向量。
- 用户已取消总预算金额上限，DeepSeek Key 已配置在 Windows 本地 `.env`。Windows 真实 API 连通烟测成功 1 次；服务端 usage 为输入 49、输出 75（含 68 推理 token），按峰时官方价格估算 US$0.0001047。烟测并非课程结果；脚本请求 `max_tokens=32` 但服务端输出超过该值，后续实验需修正并验证参数策略。
- 已核验 DeepSeek 官方文档：模型调用名为 `deepseek-flash`，支持 Tool Calls；峰时官方单价以美元计，输入未命中缓存 US$0.30/百万 token、输出 US$1.20/百万 token，使用时需重新核对。DeepSeek 思考模式默认开启；可通过 `thinking.type=disabled` 关闭。Coze 官方工作流文档列有代码、数据库查询和新增数据节点；账号、版本、权限和实际运行尚未确认。
- 已把工程模板默认 DeepSeek ID 适配为 `deepseek-flash`，添加模型/endpoint 配置与禁用自动重试；Windows 定向测试 37 passed。
- Windows `uv sync --frozen` 按锁文件安装成功；项目 `.venv` 使用 Python 3.12.7 / `win32`。上游全量测试 `194 passed, 4 skipped`；未执行需 Docker 的 4 项。
- Windows 服务与 Streamlit UI 使用明确标注的 fake model 完成一次端到端连通烟测；manifest 记有 `course_result=false`、`paid_api_request_performed=false`。不计为课程问答结果。
- 冻结 21 条课程评测用例与 6 条状态工具契约；来源清单哈希绑定在评测元数据。Windows 完整性检查通过。此状态表示规范已冻结，不代表各实现结果已通过。
- Loader、三种 Chunker、Ollama embedding、NumPy cosine 检索、持久化 Chroma 和来源过滤已实现；Windows `tests/campus -q` 当前 27 passed，涵盖工具 Runtime、Function Calling、上下文补块和跨身份拒绝。Ruff 与相关 py_compile 通过；全仓最终测试仍待最终阶段。
- 三种 chunk 配置共 475 个真实向量，维度 1024。冻结 K01–K10 本地检索中，raw NumPy Recall@1/3/5 为 0.9/1.0/1.0、MRR@5 为 0.933333；过滤后的 NumPy 与 Chroma 均为 Recall@1/3/5 1.0、MRR@5 1.0。只代表冻结题来源命中，不代表答案正确性。
- 校园 Agent 按上游 `StateGraph + ToolNode + RemainingSteps` 模式接入服务；Windows fake-mode API/UI smoke 通过。真实 DeepSeek 选中 `query_application_status` 并返回模拟 `SIM-REC-001` 状态。
- 截至 2026-10-06 18:01 的当时快照：RAG V1/V2 对同 5 题各运行一次，另有 U01/U02 边界试跑，累计 29 次回复，输入 57,872 / 输出 4,930 tokens，估算 US$0.0232776。U02 两个预期来源只命中一个（Recall@5=0.5），安全拒答正确但召回失败已记录；该失败持续保留。
- Python 原理版 NumPy/HTTPX/Pydantic Agent CLI 已有真实单例：K01 初次答案在切块断句处超出证据，增加连续块后重测已可在实际上下文找到依据。冻结 S01 首次因工具强制类别而追问；改为服务端按当前 SIM 身份与记录号解析本人行后真实调用状态工具成功。S01 实参与冻结 gold 仍有类别字段差异，原记录保留。
- Coze 包生成器字符串边界错误已修复并扩展完整性检查；H-02 已交用户核验实际工作空间费用与能力。无 Coze 调用。
- TASK-008 两路线 M01/M02 均完成：原理版使用分离 SQLite memory，工程版用上游 AsyncSqliteSaver；4 组真实对话中均按条件追问/查询，两个 M02 第二轮都真实创建本地合成工单。清空 CLI 与 SQLite 删除 API 测试通过。14 次新增模型回复，输入 30,721 / 输出 1,240 tokens，估算 US$0.0107043。
- 截至 2026-10-06 18:45，共 49 次模型回复，累计输入 109,734、输出 6,911 tokens，峰时未命中缓存估算 US$0.0413181；Coze 调用 0。账号实际账单未知；逐次用量见 `reports/API_USAGE.jsonl`。
- V1/V2 回答已基于 10 份实际输出与 trace 按统一 Rubric 评分：两版各 30/30，逐行理由见 `reports/评分表_V1_V2.csv`；评分者字段记录为 Codex。
- TASK-008 相关 Windows 定向测试 `46 passed, 6 warnings`，Ruff / `py_compile` 通过。上游真实 SQLite thread 删除集成测试也通过；完整全仓测试仍留最终阶段。

## 已披露限制与外部事项

- **H-01 / DeepSeek**：真实聊天、Function Calling、RAG、M01/M02 和冻结集/答案 Judge 已运行。本轮可量化 token 使用估算约 US$0.199506，但不是服务商账单；UI 与 Coze 实际用量未完整显示。密钥曾出现在对话中，建议账号所有者在服务商控制台轮换；不复述密钥。
- **上游使用许可问题**：实施选型资料指出指导书“从空目录建立项目”与完整模板复用的课程解释尚不明确。已准备向教师确认的问题见 `UPSTREAM.md`；得到答复前不宣称模板使用已获教师认可。
- **历史范围说明（TASK-016/021 之前）**：早期记录曾把个人信息和现场演示列为待办。我在 TASK-025 中按最终交付范围调整了这部分记录；当前评分表注明评分者为 Codex。
- **自动交付审计**：TASK-026 最新复测为 Python 原理包校园测试 35/35、工程包全量 244 passed/4 skipped；两路线独立环境均按各自锁文件同步。最终六目录包的 manifest 为 1,602 个交付内容文件逐个记录 SHA-256（不计清单文件自身）；提交报告 27 个本地链接全部解析。包不含 `.env`、测试虚拟环境或 Python 缓存。U02 的第二来源缺失已披露。
- **运行态功能测试**：FastAPI/Streamlit 本地服务实际启动，Windows 浏览器通过鼠标和键盘输入校园问答与合成状态查询；`submission/06_Demo/screenshots/engineering_ui_home_20261008.png` 及 `engineering_ui_status_20261008.png` 为原始实截图。用户亲自演示不在本技术包完成声明内。

## 当前范围与限制

- 项目文档、测试和打包工作已完成。Coze 公开发布、平台账单核验、教师许可、签字和课程现场演示均没有写成已完成；U02 的第二个预期来源仍未召回，4 个 Docker 标记测试按默认配置跳过。

## 证据路径

- 上游版本和复用范围：`UPSTREAM.md`
- 外部依赖、预算与平台状态：`reports/EXTERNAL_DEPENDENCIES.md`
- 课程要求映射：`reports/requirements_matrix.md`
- Windows 实际环境结果：`reports/WINDOWS_ENVIRONMENT.json`（TASK-001 完成时生成）
- 逐任务记录：`TASK/TASK-001.md` 至 `TASK/TASK-028.md`；Coze 平台实测见 TASK-024，范围与报告说明见 TASK-025，Windows 双路线复跑见 TASK-026，Coze H-02 更新见 TASK-027，工程版网页展示补测见 TASK-028
- RAG 对照与评分材料：`reports/Prompt_Comparison.md`、`reports/评分表_V1_V2.csv`、`reports/评分说明.md`
- 逐次模型用量：`reports/API_USAGE.jsonl`

## 完成状态

技术工作与提交副本已完成；最终复核证据见 `reports/FINAL_AUDIT.md` 和 `submission/package_manifest.json`。评分、平台账单、Coze Agent 发布、个人签署和教师许可按其真实状态披露，不以模拟材料补齐。状态与工单只使用明确标注的合成数据。
