# 校园 RAG 检索基线

日期：2026-10-06（Asia/Shanghai）。我在 Windows 项目 `.venv` 中使用 Ollama `bge-m3:latest` 做了检索实验。知识库使用 `docs/campus/source_manifest.json` 登记的 14 份资料快照；清单 SHA-256 为 `05e297bcf2fc85151e7741c9a1fa33a995d3e3b122a49630f6318c7c499c0b4c`。

## 本地向量化与分块

真实 Ollama `/api/embed` 请求共向量化 475 个校园文本块，维度均为 1024。单批 8 条，90 秒超时，无自动重试。源文件/向量均保存在 `runs/`，不写入密钥或个人数据。

| 策略 | 参数 | 文本块 | 平均字符数 | 最长 |
|---|---|---:|---:|---:|
| 固定长度 | 500 字符，重叠 80 | 147 | 470.05 | 500 |
| 递归边界 | 500 字符，重叠 80 | 213 | 338.19 | 499 |
| Markdown 标题结构 | 700 字符 | 115 | 508.22 | 699 |

## 初期三题检索观察

初期我选了冻结集中的 K01（教务规则）、K10（图书馆联系方式）和 U01（当前开放时段未知），按 source ID 计算 MRR@5。过滤策略会排除 `archive_not_for_current_answers`。固定长度向量也写入 Chroma，再用同一组 BGE-M3 查询向量检查工程版排序。完整的 10 题结果见下一节。

| 分块策略 | 原始 NumPy MRR@5 | 过滤后 NumPy MRR@5 |
|---|---:|---:|
| 固定长度 500/80 | 0.511111 | 1.000000 |
| 递归边界 500/80 | 0.333333 | 1.000000 |
| 标题结构 700 | 0.416667 | 1.000000 |

固定长度策略下，过滤后 Chroma MRR@5 为 1.000000。K10 与 U01 的原始 Top-1 是旧版图书馆页面；应用来源策略后变为当前主页快照。U01 即使检索到了主页，也不能据此回答具体开放时段。此处只测检索证据排序，未测生成式答案或未知拒答。

## 可复现记录

- 首次固定长度索引和原始检索：`runs/campus-index-20261006-173801/`
- NumPy 与 Chroma 来源策略对照：`runs/retrieval-policy-20261006-173948/`
- 三种分块策略真实向量化比较：`runs/chunking-compare-20261006-174049/`
- Windows 单元测试：`uv run pytest tests/campus -q`，10 passed。

这次只有 3 道题，MRR 仅用于小样本参数比较，不能代表 21 题冻结集或最终系统表现。政策时效、适用对象和回答引用还要结合后续 RAG/Agent 评测判断。

## 冻结知识题 10 题检索基线

Windows 重新使用冻结集 K01–K10；每题真实调用本地 Ollama BGE-M3 生成 Query 向量，在同一批记录向量上对比 raw NumPy、过滤归档来源的 NumPy 及持久化 Chroma。指标先按 `source_id` 去重，Gold 相关来源 ID 来自冻结集；每个值是 10 题的宏平均。运行共耗时 2.687 秒，无收费 LLM 调用。

| 检索实现 | Recall@1 | Recall@3 | Recall@5 | MRR@5 |
|---|---:|---:|---:|---:|
| Raw NumPy | 0.900000 | 1.000000 | 1.000000 | 0.933333 |
| 策略过滤 NumPy | 1.000000 | 1.000000 | 1.000000 | 1.000000 |
| 策略过滤 Chroma | 1.000000 | 1.000000 | 1.000000 | 1.000000 |

raw NumPy 在 K10 图书馆联系方式题中把 `library_archive_reader_rules` 和 `library_archive_hours` 排在 `library_home_2026` 前面；过滤后，NumPy 和 Chroma 都把主页排在第一位。这说明来源过滤改善了这 10 道题中的排序，不能据此推断其他问题的表现或答案质量。逐题数据见 `runs/retrieval-frozen10-20261006-180107/per_case.jsonl`。

## 真实 RAG 与 Prompt 试验

- 我让 V1 和 V2 分别回答 K01、K05、K06、K09、K10 各一次。每题都实际调用检索工具并生成答案；Top-5 证据、上下文和输出分别保存在 `runs/rag-prompt-ab-v1-20261006-175830/`、`runs/rag-prompt-ab-v2-20261006-175916/`。
- 两版五题的检索来源 Recall@1/3/5 和 MRR@5 均为 1.0。V2 固定输出“答复/依据”分区，输入 22,222、输出 1,917 tokens，峰时估算 US$0.008967；V1 输入 19,580、输出 1,485 tokens，估算 US$0.007656。V2 输出 tokens 比 V1 多 29.09%，估算费用多 17.13%。10 份回答的 Rubric 评分见 `评分表_V1_V2.csv`；两版同分，不能据此认定总体更优；具体差异见 `Prompt_Comparison.md`。
- V2 对 U01/U02 做了未知/范围边界试跑：U01 没有编出开放时段并引用图书馆首页；U02 未把国际学生流程外推给中国籍本科生，但检索只命中两个期望来源中的一个（Recall@5 0.5）。保存于 `runs/rag-unknown-v2-20261006-180143/`。

我还按统一 Rubric 给这 10 份回答逐项评分，V1、V2 都是 30/30。评分者、理由和 trace 见 [`评分表_V1_V2.csv`](评分表_V1_V2.csv) 与 [`评分说明.md`](评分说明.md)。

## Python 原理版 CLI 单例

Windows 入口为 `scripts/run_campus_principles_windows.py`，使用共用冻结向量快照、Ollama 查询向量和显式 NumPy cosine 检索，模型请求走 HTTPX Chat Completions；该入口不调用 LangGraph Agent。`--retrieval-only` 可无聊天 API 验证检索。

K01 的前两次真实运行中，模型根据 Top-1 片段未显示完的“所在学院审”扩写审批结论。只加强禁止模型记忆补全的提示没有解决问题。运行保留在 `runs/principles-20261006-182118-c183be16/` 和 `runs/principles-20261006-182229-bdf65396/`。

经查，上游工程模板的本地 Chroma 工具固定取 Top-5；AWS Knowledge Base 示例为托管 retriever，不含此本地语料的相邻文本续接机制。本项目原理版仅当 Top-1 是高长度非句末块时，按同来源 `chunk_index + 1` 增加一个相邻块，并依据源字符偏移移除重复内容。实际日志 `runs/principles-20261006-182426-2942dc1d/trace.json` 记录 anchor、continuation 和 overlap；该例从下一块剔除重叠 80 字符后补 420 字符，含完整审批句。

补块后的真实 K01 `runs/principles-20261006-182445-b9893872/` 命中冻结主答复和年份提示，且模型额外输出的审批细节现在有实际输入证据支持。该次 1 个 DeepSeek 请求，输入 3,743、输出 214 tokens，峰时估算 US$0.0013797；NumPy 查询向量 1024 维。本结果只是一个端到端原理版问题，不代表 K01 人工正确性评分、整套 RAG 评测或 21 题通过。
