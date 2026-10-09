# Prompt V1 / V2 对照实验

日期：2026-10-06（Asia/Shanghai）。我在这一天用同一组冻结问题比较了 Prompt V1 和 V2。

## 实验设置

- 问题为冻结集中的 K01、K05、K06、K09、K10；V1 和 V2 各回答一次。
- 模型：DeepSeek `deepseek-flash`；LangChain `ChatOpenAI` 兼容接口；`thinking.type=disabled`；配置 `max_tokens=768`、无自动重试。
- 相同校园 Agent、知识工具、Top-5、BGE-M3 向量、固定 500/80 分块、持久化 Chroma、来源过滤和来源清单哈希。
- 每题均发生一次真实 `search_campus_knowledge` 工具调用和一次最终模型调用；工具结果、上下文和最终答案逐题存于运行 trace。
- 每个 LLM 调用按真实 provider usage 记录；费用估算使用 DeepSeek 峰时官方价并将全部输入视为缓存未命中。价格依据：[DeepSeek 官方价格页](https://api-docs.deepseek.com/zh-cn/quick_start/pricing/)；thinking 关闭设置依据：[DeepSeek 官方思考模式文档](https://api-docs.deepseek.com/guides/thinking_mode/)。

## 结果

| 项目 | V1 | V2 |
|---|---:|---:|
| 冻结问题数 | 5 | 5 |
| 模型调用数 | 10 | 10 |
| 检索 Recall@1 / @3 / @5 | 1.000 / 1.000 / 1.000 | 1.000 / 1.000 / 1.000 |
| 来源级 MRR@5 | 1.000 | 1.000 |
| 输入 token | 19,580 | 22,222 |
| 输出 token | 1,485 | 1,917 |
| 总 token | 21,065 | 24,139 |
| 峰时估算费用（USD） | 0.007656 | 0.008967 |

V2 比 V1 多生成 29.09% 的输出 token，按同一口径估算的费用高 17.13%。两版都检索到了标准来源，因此这组结果没有显示 V2 提高了检索效果。

## 可观察差异

- V1 通常会列出来源，但不同问题的组织方式不完全相同。V2 固定分成“答复”和“依据”两部分，并明确列出文件日期、适用范围和引用链接。
- K06 的两版回答都提到了目录日期与 PDF 正文日期不一致；K09 的两版都保留了“仅适用于来华国际学生”的范围。V2 的依据写得更清楚，但回答也更长。
- 我按同一 Rubric 给 10 份回答评分，V1、V2 各 30/30。评分由 Codex 根据保存的回答和 trace 完成，结果见 [`评分表_V1_V2.csv`](评分表_V1_V2.csv)。这 10 份回答同分，不能说明 V2 在其他问题上也更好。

## 证据与限制

- V1：`runs/rag-prompt-ab-v1-20261006-175830/`，Prompt SHA-256 `39405b803feb23d38c1159a1b2260fff803d48969b3de0a39984a65be360776d`。
- V2：`runs/rag-prompt-ab-v2-20261006-175916/`，Prompt SHA-256 `fb4bdadb5f52e6d5d9c5f916f90ae6c4b4e4b6ba4d82536159c14ef6c242a53f`。
- 问题及来源版本：`evaluation/frozen_cases.json`，SHA-256 `9407a364794143c553b34ffd933ea25d4ee71a7f6e643f9dd4d0d85e55d26d44`。
- 索引使用 14 个来源，source manifest SHA-256 `05e297bcf2fc85151e7741c9a1fa33a995d3e3b122a49630f6318c7c499c0b4c`。
- 每组只有 5 题且模型有生成波动；此实验只支持相同样本下的描述性对照，不外推总体质量。
- V2 未知题结果见 `runs/rag-unknown-v2-20261006-180143/`，其 U02 来源 Recall@5=`0.5`，另列于检索失败分析；该未知边界运行不属于五题 Prompt 对照的质量均分。

## 评分

- 评分表：[`评分表_V1_V2.csv`](评分表_V1_V2.csv)，含 10 份回答的分项得分、理由、评分者与 trace。
- 评分规则：[`评分说明.md`](评分说明.md)。
