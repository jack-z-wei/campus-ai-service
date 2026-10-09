# TASK-006：真实 RAG 问答与 Prompt 对照

- 日期：2026-10-06（Asia/Shanghai）
- 状态：已完成阶段 C 的实验交付；21 题四层评测归 TASK-010，人工回答评分仍由 H-03 用户填写
- 目标：在 Windows 用已冻结校园来源、真实 Ollama BGE-M3、持久化 Chroma 和真实 DeepSeek 完成可追溯 RAG 问答；按同一组 5 题比较两个 Prompt。
- 验收：10 个知识题有 Top-1/3/5 检索证据；至少 5 个真实知识回答有 Query→Embedding→Retrieval→Context→Tool Call→Answer trace；两版 Prompt 对同 5 题实际运行；来源、年份、范围、引用、成本和未知问题如实记录。

## 已完成的实测

### 10 题检索基线（无收费模型请求）

- Windows `uv run python scripts/evaluate_frozen_retrieval_windows.py` 完成 10 个冻结知识题的查询向量与 NumPy/Chroma 对照；Ollama `bge-m3:latest`，固定 500 字符/重叠 80，Top-5，按 `source_id` 去重后计算指标。
- Raw NumPy：Recall@1 `0.900000`、Recall@3 `1.000000`、Recall@5 `1.000000`、MRR@5 `0.933333`。图书馆联系方式 K10 的旧页排在现行主页之前。
- 排除 `archive_not_for_current_answers` 后，NumPy 和持久化 Chroma 都为 Recall@1/3/5 `1.000000`、MRR@5 `1.000000`；本组 10 题未观察到过滤带来的召回退化。
- 全部 10 个查询成功，耗时 `2.687` 秒；`runs/retrieval-frozen10-20261006-180107/manifest.json` 和 `per_case.jsonl` 保存逐题来源排名。此处只评检索来源，不评答案正确性和未知拒答。

### 真实生成式 RAG

- Agent 通过真实 `search_campus_knowledge` 调用本地 Ollama 查询向量和持久化 Chroma；工具固定返回 Top-5 结果及正文、来源 ID、标题、链接、日期、适用范围、索引策略和相似度；不把不可信原始文件或报告加入索引。
- V1 Prompt 对 K01、K05、K06、K09、K10 五题各运行一次，10 次模型调用成功，来源 Recall@1/3/5 与 MRR@5 均为 `1.000000`；总 usage 输入 19,580、输出 1,485 tokens；按 DeepSeek 峰时官方单价且假设全部输入未命中缓存估算 `US$0.007656`。
- V2 Prompt 对同一五题各运行一次，10 次模型调用成功，检索指标均为 `1.000000`；总 usage 输入 22,222、输出 1,917 tokens；同口径估算 `US$0.008967`。
- `runs/rag-prompt-ab-v1-20261006-175830/` 与 `runs/rag-prompt-ab-v2-20261006-175916/` 各保存模型、提示词哈希、来源/数据集哈希、逐题问题、工具参数、检索证据、实际 usage、原始回答与延迟。
- V2 每题固定“答复/依据”分区并明确资料范围与时间限制，输出 token 总数比 V1 多 `29.09%`，峰时估算费用多 `17.13%`。两版检索表现相同；当前没有人工评分，不能据格式差异宣称 V2 的回答质量总体更高。
- V2 对未知/边界 U01 与 U02 各运行一次（4 次模型调用）。U01 回答未给出现行开闭馆时间，改引当前首页快照中的官方入口和电话；Recall@5=`1.0`。U02 明确说明 2017 年校外住宿办法只适用于来华国际学生，不能外推至中国籍本科生，拒绝给出缺乏来源的现行流程；两条期望来源仅命中一条，Recall@5=`0.5`，作为真实检索覆盖失败保留。证据在 `runs/rag-unknown-v2-20261006-180143/`。
- K01 的 V1 预试跑另存于 `runs/rag-pilot-v1-20261006-175747/`。U01/U02 与 K01 所有评分仍待用户按人工表评分。

## 观察到的限制

- 来源过滤令 10 题的来源排序上升，但不等同于答案准确率或引用正确率；U02 仍遗漏一个预期来源。
- 本项目固定 Top-5，来源级指标在 Top-5 块中按唯一 `source_id` 首次出现次序去重；`Recall@k` 与 `MRR@5` 只表示冻结 gold 来源检索。
- DeepSeek 配置每模型轮 `max_tokens=768`，关闭 thinking，自动重试为 0；各批 usage 已记录。早先 thinking 开启、请求 `max_tokens=32` 时服务端返回 75 output tokens 的现象继续保留。后续的低于 768 观测只说明本次未超限，不是普遍硬限制证明。
- 真实答案的人工正确性、忠实性和引用准确性未完成，评分材料已交给用户。

## 失败与修正记录

- 首轮 3 题的 K10/U01 曾被旧图书馆来源抢占；现有来源策略过滤后在 10 题对照中 K10 的当前主页排到首位。原始结果不覆盖。
- U02 两次语义检索均只返回 `international_off_campus_housing_2017`，没有命中预期的第二个来源 `student_management_2017`；拒答仍正确，但资料召回不完整。保留为检索失败，不修改冻结 gold。
- 早期答案的回复长度随生成变化明显；V2 格式更固定但更耗 token。实际影响和人工评分待汇总。

## 文件与证据

- Prompt：`prompts/campus_system_v1.md`、`prompts/campus_system_v2.md`
- 实验脚本：`scripts/run_rag_prompt_batch_windows.py`、`scripts/evaluate_frozen_retrieval_windows.py`
- 检索结果：`runs/retrieval-frozen10-20261006-180107/`
- 真实问答：`runs/rag-pilot-v1-20261006-175747/`、`runs/rag-prompt-ab-v1-20261006-175830/`、`runs/rag-prompt-ab-v2-20261006-175916/`、`runs/rag-unknown-v2-20261006-180143/`
- 对照报告：`reports/Prompt_Comparison.md`、`reports/RAG_Baseline.md`
- 人工评分表：`reports/人工评分表_V1_V2.csv`（10 行待评）；规则：`reports/人工评分说明.md`
- 费用逐调用记录：`reports/API_USAGE.jsonl`

## 原理版 Python CLI 补充

- 新增 `src/campus/principle_agent.py` 和 `src/campus/principle_tools.py`，使用显式 HTTP Chat Completions、Pydantic 工具参数校验、固定工具注册表和 NumPy cosine 检索；未用 LangGraph 编排原理版循环。Loader、向量快照、Prompt 与合成业务服务复用项目共有模块。
- Windows 入口 `scripts/run_campus_principles_windows.py`；`--retrieval-only` 只调用本地 Ollama/NumPy，不调用聊天 API。真实模式一次跑一题，逐模型轮保存请求 usage 和 trace；Manifest 包括来源、Prompt、冻结数据及代码 SHA-256。
- 首次真实 K01 `runs/principles-20261006-182118-c183be16/` 正确给出学分区间，但多答的审批结论只在下一文本块中补全；即使增加“不得补全被截断句子”的提示，`runs/principles-20261006-182229-bdf65396/` 仍复现。保留两个回答作为失败证据。
- 已查上游 `src/agents/tools.py` 的通用 Chroma Top-K 和 `knowledge_base_agent.py` 的托管检索接口；未找到按相邻块/原文偏移补上下文的实现，未强行复用。改用校园固定块 `chunk_index` 和源字符偏移，仅在 Top-1 块被截断时补入同文档后一块，并记录 overlap/新增长度。
- Windows 本地检索复验 `runs/principles-20261006-182426-2942dc1d/` 表明 K01 补入后一块、去掉重复 80 字符，完整审批句在实际上下文中。真实 K01 复测 `runs/principles-20261006-182445-b9893872/` 为一次模型请求（输入 3,743、输出 214 tokens，峰时估算 US$0.0013797）；本次答案的额外审批句与年份/效力提醒均有送入模型的证据支持。该结论仅限 K01 单例，未代替完整评测或人工评分。
- Windows `tests/campus -q` 在补块后 `25 passed`；状态类别工具可选解析更新后 `27 passed`；相关代码 Ruff 和 py_compile 通过。最终完整测试待后续阶段结束前执行。
