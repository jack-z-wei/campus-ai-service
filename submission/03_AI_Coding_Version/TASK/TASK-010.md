# TASK-010：固定集四层 Evaluation 与基线

- 日期：2026-10-06（Asia/Shanghai）
- 状态：已验收（自动化基线与评分材料完成；人工评分另列待办）
- 数据集：`campus-customer-service-frozen-v1`，冻结 21 个用例、按多轮拆分为每条路线 23 个 assistant turn。
- 指标规范：`evaluation/metric_spec_v1.json`（v1.1）。

## 交付与证据

- 指标实现：`src/campus/evaluation_metrics.py`；已知结果夹具及 Windows 测试：`tests/campus/test_evaluation_metrics.py`。
- Windows 基线批处理：`scripts/run_frozen_baseline_windows.py`；离线聚合：`scripts/evaluate_frozen_metrics_windows.py`。
- 原始单例 trace、每例 manifest 与父级索引：`runs/baseline-principles-v1-20261006/`、`runs/baseline-engineering-v1-20261006/`。
- 四层逐轮 evidence、Judge 输入/原始输出、重算结果：`runs/frozen-eval-v1-20261006/`。
- Judge 标准：`prompts/campus_evaluation_judge_v1.md`；V1/V2 空白人工表及规则：`reports/人工评分表_V1_V2.csv`、`reports/人工评分说明.md`。

## 真实基线摘要

| 指标 | Python 原理版 | LangGraph 工程版 |
|---|---:|---:|
| 逐轮 trace | 23/23 | 23/23 |
| Retrieval Recall@1 / @3 / @5 | 0.9583 / 0.9583 / 0.9583 | 0.9583 / 0.9583 / 0.9583 |
| Retrieval MRR@5 | 1.0000 | 1.0000 |
| Tool Selection Accuracy | 9/11 = 0.8182 | 21/23 = 0.9130 |
| Tool Argument Accuracy | 6/8 = 0.7500 | 6/8 = 0.7500 |
| Task Completion Rate | 21/23 = 0.9130 | 21/23 = 0.9130 |
| Unknown Handling | 2/2 | 2/2 |
| Answer Correctness（Judge 2 分） | 23/23 | 23/23 |
| Answer Faithfulness（Judge 2 分） | 23/23 | 23/23 |
| Citation Accuracy（适用题；Judge 2 分） | 12/12 | 12/12 |
| 平均 / P95 延迟 | 2189.6 / 4968 ms | 3701.1 / 4719 ms |
| 运行错误率 | 0/23 | 0/23 |

来源命中失败集中在 U02：期望两个 `source_id`，只检索到 `international_off_campus_housing_2017`，Recall@5=0.5。S04 和 B01 造成两条路线各自 2 个工具/任务完成差异。S01 状态正确，但实际参数省略 `service_type`；服务端在当前合成身份范围内安全解析，仍按冻结 gold 记参数不匹配。

Judge 使用 `deepseek-flash`，与生成模型同属一个模型系列；以上自动分数只是模型辅助代理，不是人工评分或独立验证。Citation 只在有 gold 来源的 12 个 turn 计分；其余 11 个是 N/A。H-03 的 10 份 V1/V2 人工评分保持空白待用户填写。

Engineering 延迟是完整 LangGraph `ainvoke` 墙钟时间；Principles 延迟是检索时间加 API round-trip，范围不同，不能直接比较。P95 使用最近秩定义。Windows 初始全套测试 237 passed / 1 failed / 4 skipped；修复 Streamlit 可选参数后为 238 passed / 0 failed / 4 skipped。基线测试通过率 237/238=0.9958，修复后 238/238=1.0，skip 单独列出。
