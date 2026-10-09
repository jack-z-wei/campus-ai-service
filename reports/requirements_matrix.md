# 课程要求与交付映射

表中“待做”表示目前没有对应记录。单有代码或文档不算完成；学校来源和人工评价只有实际核验后才更新状态。

| 要求 | 实现范围 | 责任人 | 验收方式 | 证据目标 | 状态 |
|---|---|---|---|---|---|
| 校园知识库 ≥10 份、≥2 类 | 长安大学公开教务、奖助学金、宿舍、图书馆资料 | 我 | 来源清单、正文、主题数量、哈希、日期 | `docs/campus/source_manifest.json`、`docs/campus/*.md` | 已完成：14 份、4 类；现行效力逐条标注 |
| Loader 与数据清洗 | 仅导入来源清单中的校园资料；保留元数据、核对来源 hash、拒绝损坏/越界文件 | 我 | Windows 单元测试和文档统计 | `src/campus/ingestion.py`、`tests/campus/` | 已完成：只加载清单 14 份来源 |
| 三种 Chunking | 固定长度、递归边界、标题结构；对比检索变化，禁止跨文档拼接 | 我 | 计数、长度分布、检索结果 | `src/campus/chunking.py`、`runs/chunking-compare-20261006-174049/` | 三种参数真实向量化已完成；冻结集 10 题检索完成 |
| Embedding 与相似度 | Ollama BGE-M3，真实向量化至少 20 chunks | 我 | Windows Ollama 推理、维度、相似度和失败记录 | `src/campus/embeddings.py`、`runs/`、`reports/RAG_Baseline.md` | 已完成：475 个策略变体块，1024 维 |
| Retrieval / RAG | NumPy 原理版、Chroma 工程版；Top-1/3/5、真实 RAG 问答、引用和未知拒答 | 我 | 冻结配置，追踪实际 evidence 与答案，运行至少 10 知识题 | `src/campus/retrieval.py`、`src/campus/retrieval_chroma.py`、`runs/` | K01–K10 冻结检索、真实生成、未知 U01/U02 与两路线评估均已留档；U02 第二来源未召回，明确保留缺陷 |
| LLM 与 Prompt 实验 | 当前 DeepSeek Flash；2 种 Prompt 对同 5 题比较 | 我（本机配置 Key） | Windows 真实调用与 tool-call 协议；没有 Key 时不伪造结果 | `prompts/`、`runs/rag-prompt-ab-*` | 同 5 题真实 V1/V2 已跑；10 份回答按统一 Rubric 各版本 30/30，见 `评分表_V1_V2.csv` |
| 状态查询工具 | SQLite 模拟申请，输入校验、身份约束、参数化 SQL | 我 | 3 正常、2 错误、1 不存在 | `src/campus/tools/`、`data/campus/simulation_records.json`、`tests/campus/` | 工具契约和 Agent 图内注入测试通过；真实模型状态工具调用成功 |
| 模拟人工转接 | 创建唯一工单，返回 id/reason/status/timestamp | 我 | 正常、幂等、错误和持久化测试 | `src/campus/tools/`、SQLite | 工具契约通过；原理版和工程版 M02 第二轮均真实 Function Call 并写入本地模拟工单；未联系真人 |
| Agent / Function Calling | 真实模型决策，结构化工具参数校验、结果回传、有限循环、超时 | 我（已配置并授权 Key） | API trace 与集成结果 | `src/agents/campus_customer_service.py`、`runs/` | 基线与优化版各 21 个冻结案例已运行；本地状态/模拟工单调用、Windows 浏览器截图和 Coze 测试均已留证 |
| Memory | 有界会话上下文，追问、指代、跨轮工具调用、隔离和清空 | 我 | 至少两组真实多轮对话 | 源码、固定集结果和 trace | 两路线各 M01/M02 多轮已记录；身份切换隔离回归、上下文上限与清理定向测试通过 |
| 固定评测集 | 项目约定 21 题：知识10、状态5、多轮2、未知2、边界2；人工转接另测 | 我 | 校验字段、冻结来源哈希，不以模型输出反推答案 | `evaluation/frozen_cases.json`、`evaluation/status_tool_contract.json` | 已冻结并在基线/优化两版双路线真实运行；原始 evidence 保留 |
| 四层 Evaluation | Retrieval、Answer、Agent、Engineering 指标、分类/逐题原始结果 | 我；Rubric 评分由 Codex 完成 | 定义分母和 N/A、运行 Manifest、原始 trace 可重算 | `src/campus/evaluation_metrics.py`、`runs/frozen-eval-v1-20261006/`、`runs/frozen-eval-optimized-v1-20261006/`、`评分表_V1_V2.csv` | 自动指标、Judge、原始工件完成；另有 10 份 V1/V2 回答按 Rubric 评分，各 30/30 |
| 真实失败与工程改进 | 保留失败证据，至少三项真实工程改进，基线和优化冻结集对照 | 我 | 来源代码/trace 可核验，不刻意制造失败 | `reports/Failure_Analysis.md`、`evaluation/failure_cases.json`、`reports/Optimization_Comparison.md`、`TASK/TASK-012.md`、`TASK/TASK-013.md` | K01 切块截断、K10 归档资料排序、U02 第二来源漏召回为三个不同真实 query；前两项有修复后 trace，U02 仍未解决；身份隔离/工具门控等工程改进也有证据 |
| Coze 独立版本 | 知识、两套分段实验、两个模拟业务工具、多轮和未知问题 | 我 | 至少 10 题与 2 个三轨对照问题独立执行；依 H-02 留存真实配置、工作流与运行证据 | `coze/`、`TASK/TASK-024.md`、`reports/Coze_Python_Engineering_Mapping.md` | H-02 技术交付项满足：原始集14题/16轮、两组切分、状态/转接工作流与三轨输出均有证据；原始5条 partial、7个未在 Coze 运行的冻结题及不可观测字段如实披露。2026-10-08 提示词修订后另有3条同题复测，K09通过，K01/K06仍为partial；Agent为草稿，账单和部分trace未知 |
| 三轨对照 | 同一个知识题和明确参数的状态题，Coze/原理版/工程版各运行 | 我 | 至少 6 个独立结果、记录配置差异 | `reports/three_track_comparison.csv`、`reports/Coze_Python_Engineering_Mapping.md` | K01、S02 各三路线实测，共 6 行结果，配置差异已记录 |
| AI 工程复用与过程 | 保留上游许可和改动范围，独立原理版、TASK 记录 | 我 | 查验许可证、代码来源与实际任务证据 | `UPSTREAM.md`、`TASK/` | MIT LICENSE 和来源/改动范围已披露；未声称取得教师许可 |
| 报告、Demo、提交包 | 报告模板技术章节、六类交付、Windows PowerShell 操作说明 | 我 | 所有数字回链原始证据，缺项明确，不冒称课程官方验收 | `reports/final_report.md`、`submission/` | 报告已填入我提供的课程、学生、学号和指导教师信息；Windows 页面、Coze 截图、六类材料和哈希清单已整理。报告只记录有证据支持的技术工作；没有签字、教师许可、现场演示或正式提交记录。 |

## 评测口径

- 课程文件在题目数量和章节安排上存在差异。我按实施计划冻结了 21 个评测用例，并在报告中说明这是本项目采用的口径。
- 我从 Windows `.venv` 启动服务、安装依赖并做最终运行检查。WSL 中的文件修改本身不作为 Windows 运行证据。
- 只有实际调用 DeepSeek 的记录才计作真实模型实验；Fake/Mock 只用于软件协议测试，并在记录中标明。
- 模拟申请与工单须在界面和报告中标明；公开政策资料须有来源、年份和实际适用范围。
- Coze 原始结果、未运行的冻结题和提示词修订后的复测分开记录，原有 partial 结果继续保留。平台没有展示的字段标作无法观测；评分依据见评分表。没有完成的签字、现场演示、教师许可和课程平台提交，不写成已完成。
