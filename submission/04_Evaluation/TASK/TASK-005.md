# TASK-005：校园资料索引与本地 RAG 基线

- 日期：2026-10-06（Asia/Shanghai）
- 状态：已完成（资料加载、三类分块、本地向量化、NumPy/Chroma 检索基线）
- 目标：仅基于来源 manifest 登记的校园资料建立 Windows 可运行的加载、分块、embedding 和检索实验；隔离未登记的探索文件和上游模板样例。
- 验收：至少 20 个真实校园文本块调用本机 Ollama `bge-m3:latest`；记录维度、分块数量/长度分布、相似度结果和失败；同一来源不能跨文档合块；产生可复现的 Top-1/3/5 检索基线。

## 已完成的前置检查

- TASK-004 的评测集及来源版本哈希已在 Windows 校验通过。
- 已在 Windows 虚拟环境编译检查 API 冒烟脚本，真实 `deepseek-flash` 连通请求成功：输入 49 token、输出 75 token（含 68 推理 token），响应内容为预期短句；记录于 `runs/api-smoke-20261006-173028/manifest.json`。该请求只证明网络/API 连通，不是课程题答复。
- 首次运行因启动脚本没有将 `src` 放入模块路径而在发请求前失败。已修正脚本导入路径并保留本条失败记录；无请求、无 API 费用。
- 对真实响应发现请求 `max_tokens=32`，但服务端 usage 返回 75 个输出 token。用量按服务端记录，之后需验证思考模式与 token 上限策略。
- 依据官方最新价格页修正了费用单位：DeepSeek 价格以 USD/百万 token 标注。之前的 `estimated_cost_cny` 是错误派生字段，修正过程和新估算保留在 `reports/API_USAGE_ADJUSTMENTS.jsonl`；按峰时价格保守估算本次为 US$0.0001047。

## 尚未完成

- 生成式 RAG 问答与固定集知识题答案评测由后续 Agent/RAG 任务完成；当前只测检索证据排序，未知题答案正确性未测。
- DeepSeek OpenAI-compatible wrapper 的 token 上限与思考模式行为仍需在真实课程 Agent 调用中验证；不得把 `max_tokens=32` 作为已证明的硬上限。
- Coze 版本及 UI 平台运行由后续人工配置包和用户实测完成。

## 已完成实现与实测

- `src/campus/ingestion.py` 只从 `source_manifest.json` 读取 14 个登记的 Markdown；每个来源核验原件 SHA-256，拒绝路径越界、损坏或空文件。
- `src/campus/chunking.py` 实现固定长度、递归边界和 Markdown 标题结构三种分块；分块元数据含来源、策略、偏移和字符数。
- `src/campus/embeddings.py` 通过本机 Ollama `/api/embed` 批量生成 BGE-M3 向量；单批 8 条、90 秒超时、无自动重试，校验向量数、维度和有限值。
- `src/campus/retrieval.py` 实现可复算的 NumPy cosine Top-K；`src/campus/retrieval_chroma.py` 实现带持久化、关闭遥测和来源策略过滤的 Chroma 索引。
- Windows `uv run pytest tests/campus -q`：10 passed；源码及实验脚本通过 Windows `py_compile`。
- 固定长度 500/重叠 80：147 块；递归边界 500/重叠 80：213 块；标题结构 700：115 块。三种分块的本地 BGE-M3 向量实测均为 1024 维，共计 475 个策略变体向量。
- 原始检索三题 MRR@5：固定长度 0.511111、递归边界 0.333333、标题结构 0.416667；过滤 `archive_not_for_current_answers` 后，三种 NumPy 变体均为 1.0。固定长度策略的 Chroma 过滤检索 MRR@5 为 1.0，与 NumPy 排名一致。
- 三题只含 K01、K10 和未知题 U01；样本很小。U01 是否答出“无法确认开放时段”尚未评估，不把来源命中记为答案通过。
- 初轮发现图书馆联系方式/当前开放时间命中旧版馆时和借阅页面。保留原始错误结果并新增来源策略过滤；对照证据见 `runs/campus-index-20261006-173801/`、`runs/retrieval-policy-20261006-173948/` 和 `runs/chunking-compare-20261006-174049/`。
- 首次索引实验单元测试因测试夹具的 metadata 未含 `source_id` 失败；为所有 chunk metadata 强制写入 `source_id` 后，当前 10 项 Windows 测试通过。失败过程未删除。

## 文件与证据

- 模块：`src/campus/ingestion.py`、`src/campus/chunking.py`、`src/campus/embeddings.py`、`src/campus/retrieval.py`、`src/campus/retrieval_chroma.py`
- 脚本：`scripts/run_campus_index_windows.py`、`scripts/evaluate_policy_filter_windows.py`、`scripts/compare_chunkers_windows.py`
- 结果：`reports/RAG_Baseline.md`、上述 `runs/` 中的 manifest、逐批进度、chunks、向量和 Top-5 排名
