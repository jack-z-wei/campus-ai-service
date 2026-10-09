# TASK-012：基于审计的工程改进

- 日期：2026-10-06（Asia/Shanghai）
- 状态：已验收（工程改进、Windows 回归和同冻结集优化复测均完成）
- 冻结基线：`runs/frozen-eval-v1-20261006/`
- 改动边界：未修改 `evaluation/frozen_cases.json`、标准答案或历史真实失败。

## Before / Problem / Change / After

### 1. 按模拟身份隔离 checkpoint 对话，门控个人业务工具

- **Before**：同一 Streamlit thread 更改 `simulation_user_id` 后，checkpoint 中上一身份的用户问题、工具结果和回复继续发送给模型；无身份时，状态查询仍作为可选工具暴露。S04 基线两路线都调用了状态工具，虽然工具返回 `invalid_identity` 且没有泄漏记录结果。
- **Problem**：只在业务工具执行处校验身份无法阻止旧工具结果进入下一身份的模型上下文；无身份时模型仍可误选个人状态工具。
- **Change**：工程版图入口新增身份范围节点；身份改变或旧 checkpoint 缺少身份标记时清除旧对话；Principles 与工程版在无有效模拟身份时只把知识搜索暴露给模型；工程版在 `ToolNode` 前拒绝模型返回的未授权工具名。提示词区分已配置身份与未配置身份。
- **After**：修复前 Windows checkpoint 集成挑战断言失败（第二次模型输入包含“材料审核中”）；修复后同一回归测试通过。无身份工具门控与两条路由的定义过滤测试也通过。证据见 `evaluation/challenge_cases_v1.json`、`tests/campus/test_agent_integration.py`、`tests/campus/test_principle_agent.py`。

### 2. 修复 Streamlit 可选 agent 配置传参

- **Before**：没有额外身份配置时仍向 `AgentClient.ainvoke/astream` 显式传 `agent_config=None`，违反上游客户端按需省略可选参数的调用约定，导致原全量测试 `237 passed, 1 failed, 4 skipped`。
- **Problem**：普通非校园 Agent 页面路径也会受到校园配置扩展影响。
- **Change**：仅在 `agent_config` 实际非空时将它加入客户端参数。
- **After**：本次改动后的 Windows 全量测试 `241 passed, 0 failed, 4 skipped`，18 warnings，53.99 秒。Docker 标记的 4 项仍跳过并单独计数。

### 3. 避免评估器跨版本复用旧多轮 trace，修正 Windows manifest 路径回退

- **Before**：工程版 TASK-008 多轮 manifest 无代码 fingerprint；评估批次目录曾因 Windows/WSL 路径表示无法解析 child manifest，第一次离线聚合失败。若直接复用旧多轮记录，会将修改前 trace 错标成优化版。
- **Problem**：这会影响阶段 E 的基线与优化对照可追溯性，而且重复运行模型不是修复路径问题的必要条件。
- **Change**：多轮 runner 记录 agent/tools/RAG/status 实现文件哈希及 Prompt、来源清单、冻结集哈希；复用逻辑只有在这些指纹一致时接受历史记录。批次索引以稳定 child `run_id` 修复路径，聚合器可据此回退定位。
- **After**：当前代码指纹和 TASK-008 工程版、Principles 旧实现均不一致，复用探测返回 `None`，保证优化多轮会重跑。原冻结基线使用已保存 M01/M02 trace 离线聚合到每路线 23 turns、46 份 judge input，没有重复付费生成。

### 4. 修正四层评估结果中的 Judge 状态标记

- **Before**：46 个答案 Judge 已完成，但汇总 JSON 的顶层 `answer_judge_pending` 仍固定为 true。
- **Problem**：报告的机器可读状态与逐路线答案指标不一致。
- **Change**：聚合器按完成/待判定结果设置顶层状态，并增加优化路线 ID 参数。
- **After**：基线重算成功，23 turn/route、46 judge input；输出状态反映全部 Judge 已完成，并可直接为 TASK-013 指定新运行目录重算。

## 验收条件

- [x] 至少三项有审计证据的代码/工程改进。
- [x] 相关 Windows 定向测试、Ruff、`py_compile` 通过。
- [x] 对两路线用完全相同的 21 例重新生成优化版 run，重算四层指标及答案 Judge。
- [x] 更新前后差异图表与 `reports/Agent_Evaluation.md`、`reports/Optimization_Comparison.md`。

## TASK-013 的冻结集复测结果

- 原理版与工程版优化运行均重新执行 21/21 案例、23/23 assistant turns；共 46 份 Judge 全部完成。代码、Prompt、来源与冻结集指纹已进入 run manifest；旧 M01/M02 trace 因代码指纹不一致而没有复用。
- S04 身份未配置场景两路线均不再调用个人状态工具，任务完成率均从 21/23 升至 22/23；Tool Selection 分别升至 10/11、22/23。
- 真实退化同样记录：Principles Tool Argument 从 6/8 降至 5/8，原因是优化运行的 S05 省略 `service_type`；没有为提升总体分数改写 frozen gold。
- U02 仍为 Recall@5=0.5；B01 保留安全拒绝与 gold 工具合同冲突。判分器与生成模型同系列，Judge 满分不代替 H-03 人工评分。
- Windows 全量 suite 最终为 241 passed、0 failed、4 skipped、18 warnings；4 项 Docker 测试因未启用 Docker 标记而跳过。图表 XML 已由 Windows 项目 Python 解析通过。
- 可重算结果、差异表和图表见 `TASK/TASK-013.md`、`reports/Agent_Evaluation.md`、`reports/Optimization_Comparison.md`。
