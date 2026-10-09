# 检索优化对比

## 实际改动

最初的索引也包含了旧版图书馆页面，检索时它们有时会排在当前主页前面。我保留原始索引和结果，并在 NumPy、Chroma 两条检索接口中加入 `exclude_index_policies`，让当前知识问答跳过 `archive_not_for_current_answers` 标记的资料。

## 小样本对照

查询为冻结集 K01、K10、U01；相关来源排名按 MRR@5 计算。

| 检索配置 | K01 来源排名 | K10 来源排名 | U01 来源排名 | MRR@5 |
|---|---:|---:|---:|---:|
| 固定分块 NumPy 原始 | 1 | 3 | 5 | 0.511111 |
| 固定分块 NumPy 策略过滤 | 1 | 1 | 1 | 1.000000 |
| 固定分块 Chroma 策略过滤 | 1 | 1 | 1 | 1.000000 |

过滤后，图书馆联系方式题从旧版读者须知改为命中当前主页；U01 也不再检索到旧开放时间页面。不过，主页快照没有具体开放时段，系统仍应说明现有资料无法确认。本次只比较了检索结果，没有运行或评分 LLM 答案。

三种分块策略在这 3 题上的原始 MRR@5 分别为：固定长度 0.511111、递归边界 0.333333、标题结构 0.416667。加入来源过滤后，三种策略的 MRR@5 都是 1.0。样本较小，我只把它作为本次参数比较记录；结果见 `runs/chunking-compare-20261006-174049/manifest.json`。

## 证据

- 原始检索：`runs/campus-index-20261006-173801/`
- NumPy/Chroma 过滤对照：`runs/retrieval-policy-20261006-173948/`
- 分块参数对照：`runs/chunking-compare-20261006-174049/`

## 冻结知识集 10 题复测

重新运行 K01–K10 后，raw NumPy 的 source-level MRR@5 为 0.933333，Recall@1 为 0.900000；过滤 `archive_not_for_current_answers` 后，NumPy 和 Chroma 的 MRR@5 与 Recall@1/3/5 均为 1.000000。来源策略过滤在这批冻结问题中提升 K10 的主页排名，其他九题保持首位来源命中。每个数值都来自 10 个冻结题，详细排名见 `runs/retrieval-frozen10-20261006-180107/`。

U02 是例外和后续任务：过滤策略下检索到其两条 gold 来源中的一条，Recall@5=`0.5`；回答正确拒绝把国际学生流程外推给中国籍本科生，但检索覆盖仍失败。见 `runs/rag-unknown-v2-20261006-180143/traces/U02.json`。不能只用总体平均值掩盖这条失败。

## Prompt 结构变化对照

V2 增加固定“答复/依据”结构。五题中 V2 五份回答都出现两个分区；V1 五份没有完整同时出现这两个显式分区。两版的检索 Recall@1/3/5 与 MRR@5 相同，均为 1.0。V2 消耗更多：输出从 1,485 增至 1,917 tokens（+29.09%），峰时估算费用从 US$0.007656 增至 US$0.008967（+17.13%）。

在保存的 5 个回答中，V1 没有完整使用这两个分区，V2 则 5 个都使用了。10 份回答的统一 Rubric 评分见 `reports/评分表_V1_V2.csv`，两版均为 30/30。这个格式变化本身不能说明正确性或忠实度有所提高。

## Agent 四层冻结集优化对照

阶段 E 的代码改进和完整四层结果见 [`reports/Agent_Evaluation.md`](Agent_Evaluation.md)。两版各重新执行同一冻结集 21 个用例、23 个 turn/路线，并对 46 份答案分别完成同方法的模型辅助 Judge。

可归因于 S04 身份门控的变化是：两路线不再向模型暴露/执行未认证状态工具；Tool Selection 提高，Task Completion 两路线各提升 1/23。B01 的拒绝工具调用与 gold 合同冲突仍保留。U02 的检索 Recall@5 仍为 0.5，没有适用的国内本科生现行住宿材料可用于安全修复。

总体上，Principles Tool Argument Accuracy 从 6/8 降为 5/8（优化版 S05 省略可选服务类别，虽然正确返回 not_found）；Engineering 维持 6/8。Answer Judge 与生成器同系列；Prompt V1/V2 的 10 份样本按统一 Rubric 各得 30/30，见 `reports/评分表_V1_V2.csv`，该小样本同分不证明 V2 总体更优。延迟方面 Engineering 平均和 P95 变高、Principles 平均略高而 P95 降低；每项仅一轮运行样本，报告原始变化而不作性能归因。

图表由 Windows 脚本 `scripts/generate_optimization_charts_windows.py` 生成：`reports/optimization_quality_metrics.svg`、`reports/optimization_latency_metrics.svg`。
