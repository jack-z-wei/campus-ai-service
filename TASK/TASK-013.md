# TASK-013：优化版冻结集复测与对照

- 日期：2026-10-06（Asia/Shanghai）
- 状态：待人工（本地复测、自动评分、对照报告与图表已完成；H-03 的 10 份真实人工评分未填写）
- 冻结集：`campus-customer-service-frozen-v1`；21 个案例，每路线展开为 23 个 assistant turns。
- 优化评测：`runs/frozen-eval-optimized-v1-20261006/`
- 基线评测：`runs/frozen-eval-v1-20261006/`

## 已完成的自动化交付

- Principles 与 Engineering 各从优化版代码重新运行 21/21 案例、23/23 turns；没有复用指纹不匹配的 TASK-008 多轮 trace。两个父运行及逐轮 manifest 记录实现、提示词、来源清单和冻结集指纹。
- 两版共 46 条答案 Judge 输入均完成，`answer_judge_pending=false`。Judge 是与生成器同系列的 `deepseek-flash`，只作为模型辅助指标；不能替代独立人工评价。
- Windows 项目环境离线重算基线与优化版四层指标；两套结果均为 23 turns/route、12 个适用检索 turns/route、0/23 执行错误。重算没有发出模型/API 请求。
- 生成 `reports/optimization_quality_metrics.svg` 和 `reports/optimization_latency_metrics.svg`；Windows 项目 Python `xml.etree.ElementTree` 解析两张 SVG 均通过。
- `reports/Agent_Evaluation.md` 包含完整 before/after 指标、样本分母、Judge 局限、延迟口径和原始证据索引；`reports/Optimization_Comparison.md` 已关联 Agent 对照。

## 冻结集对照摘要

| 指标 | Principles 基线 → 优化 | Engineering 基线 → 优化 |
|---|---:|---:|
| Retrieval Recall@5 | 11.5/12 → 11.5/12（0.9583） | 11.5/12 → 11.5/12（0.9583） |
| Tool Selection | 9/11（0.8182）→ 10/11（0.9091） | 21/23（0.9130）→ 22/23（0.9565） |
| Tool Argument | 6/8（0.7500）→ 5/8（0.6250） | 6/8（0.7500）→ 6/8（0.7500） |
| Task Completion | 21/23（0.9130）→ 22/23（0.9565） | 21/23（0.9130）→ 22/23（0.9565） |
| Unknown Handling | 2/2 → 2/2 | 2/2 → 2/2 |
| 执行错误率 | 0/23 → 0/23 | 0/23 → 0/23 |

答案 Judge 的正确性、忠实性均为各路线 23/23 满分；有 gold 来源的引用准确性为 12/12，另 11 turns 不适用。由于生成和 Judge 同系列，结果不视为独立确认。优化版 Principles 平均/P95 为 2242.6/2875ms；Engineering 为 4343.8/6141ms。其基线/优化差异只有单次运行样本，且两路线计时范围不同，不据此主张性能变化由代码导致。

## 问题与未满足验收项

- S04 无身份时的状态工具暴露已由优化解决；身份切换造成 checkpoint 旧结果进入下一用户上下文的缺陷有独立 Windows 回归测试，详见 TASK-011/012。
- U02 每条路线优化后仍只命中两个 gold 来源中的一个，Recall@5=0.5。五个运行观察只有一个不同查询，不满足“三个独立检索失败场景”；没有伪造额外场景或不适用的国内本科生政策。
- B01 的冻结 gold 要求发起其他用户记录查询并收到 `forbidden`，模型仍直接安全拒绝；保留 gold 与真实行为冲突，不诱导越权查询。
- Principles Tool Argument 降至 5/8，优化运行 S05 少传 `service_type`，虽然该合成记录返回 `not_found`；此退化如实保留。
- H-03：`reports/人工评分表_V1_V2.csv` 仍为 10 行空白评分，缺少用户真实评分/理由/评分人/日期。因此人工均分与课程人工验收待完成。

## 验证和证据路径

- Windows 全量测试：`.venv\\Scripts\\python.exe -m pytest -q`，241 passed / 0 failed / 4 skipped / 18 warnings，53.99 秒。4 个 Docker 标记用例保持跳过；摘要见 `runs/windows-test-summary.json`。
- Ruff 与 Windows `py_compile` 对本轮修改的应用源码、测试和脚本通过；图表脚本已实际在 Windows 项目 Python 执行。
- 基线与优化逐轮数据、Judge 原始输出、指标结果：`runs/frozen-eval-v1-20261006/`、`runs/frozen-eval-optimized-v1-20261006/`。
- 两版按案例父级清单：`runs/baseline-principles-v1-20261006/`、`runs/baseline-engineering-v1-20261006/`、`runs/baseline-optimized-principles-v1-20261006/`、`runs/baseline-optimized-engineering-v1-20261006/`。
- 失败案例和数量审计：`evaluation/failure_cases.json`、`reports/Failure_Analysis.md`。

## 人工交接

H-03 的表格和规则已准备好，见 `reports/HUMAN_TODO.md`。需要用户在 Windows Excel/兼容表格工具中打开 `reports/人工评分表_V1_V2.csv`，按 `reports/人工评分说明.md` 为 K01、K05、K06、K09、K10 的 V1/V2 共 10 个回答填写正确性、证据忠实性、引用准确性三项 0/1/2 分及理由、评分人和真实日期，再保存原 CSV。验收时以 10 行完整且内容由用户实际评出为准；Luna 不补填。

Coze 平台实测、教师对上游模板的许可和个人报告字段不属于本任务自动结果，分别跟踪于 H-02、H-07、H-04。
