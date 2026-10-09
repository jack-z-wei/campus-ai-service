# Coze 平台配置与实测现状

更新时间：2026-10-08。以下是截至本次归档的实际配置与证据索引，不是待执行的界面操作清单。

## 已配置的平台资源

| 资源 | 实际状态 | 证据 |
|---|---|---|
| 校园客服知识库-A | 14 份文档、平台显示 2,084 片；Agent 最终挂载 A | `../screenshots/01A_校园客服知识库A.png` |
| 校园客服知识库-B | 14 份文档、平台显示 2,365 片；用于 K01 A/B 同题观察 | `../screenshots/01B_校园客服知识库B.png`、`../screenshots/22_Agent-知识库B同题检索.png` |
| application_status | 单用户模式；4 条 SIM 合成测试数据，`simulation_only=true` | `../screenshots/02A_application_status表结构.png`、`../screenshots/02B_application_status模拟数据.png` |
| 长安大学校园智能客服 | 单 Agent 自主规划，页面显示豆包·2.0·pro；已连 A 库和两个工作流；草稿未公开发布 | `../screenshots/03_Agent与K01.png`、`../screenshots/05_Agent工作流接入.png`、`../screenshots/25_Agent-K01-三轨同题基线.png` |
| campus_service_status_query | 工作流 ID `7693891212118818854`；按 record_id、service_type、owner_sim_user_id AND 查询，最多返回一条 | `../screenshots/04_Agent工作流状态查询.png`、`../screenshots/workflow-status-owner-match.png`、`../screenshots/workflow-status-cross-user-empty.png`、`../screenshots/workflow-status-published.png` |
| campus_human_service_demo | 工作流 ID `7693901471003689023`；个人空间有发布版本；完成合成数据直接试跑及 Agent M02 调用 | `../screenshots/06_campus_human_service_demo流程.png`、`../screenshots/07_campus_human_service_demo发布记录.png`、`../screenshots/21_Agent-M02-查询后创建模拟工单.png` |

## 已执行验证

- Coze 用例：14 题、16 个助手轮次，分类覆盖知识、状态、多轮、未知和边界；逐条真实答案和偏差在 `../results.csv`，原始概览在 `../logs/agent-evaluation-20261007.md`。
- 切分对照：知识库 A/B 使用不同实际分段配置，对 K01 留有独立回答；设置、输出和限制在 `../experiment_sheet.csv`。
- 检索参数：K01 在 Top-K 5 / 0.50 与 Top-K 3 / 0.70 各有真实运行，结束时恢复 Top-K 5 / 0.50；见 `../retrieval_parameter_comparison.csv`。
- 三轨对照：K01 和 S02 在 Coze、Python 原理版、LangGraph 工程版分别运行，六份独立答案在 `../../reports/three_track_comparison.csv`。
- 状态工作流直接验证了 owner 匹配、跨 owner 和无记录；截图见上表。
- M02 的 Agent 运行明确请求后实际写入一条模拟工单，返回平台可见 ID；这不联系真人。

## 保留的结果偏差与平台限制

- Coze 逐题表有 14 个已运行结果，其中 5 个标为 partial；这些原始结果未用 prompt 改写或本地答案替代。逐题解释见 `../results.csv`。
- 7 个冻结用例没有在 Coze 执行，结果表相应字段保持空白。
- Agent 预览没有为每条运行导出完整 workflow arguments、全部来源 ID 或稳定 run ID；个别截图不能证明节点是否调用，具体见逐题限制。
- 转接 workflow 的 request_key 去重、关联状态 owner 二次校验和异常补偿没有经过本次验证。
- SIM 身份是演示输入，不是登录认证；工单是合成数据，不会通知真人。
- Agent 保持个人空间草稿；平台账单、余额和 embedding 单价没有在界面核验。

课程 H-02 技术证据已按 `../验收补齐清单.md` 归档。除非教师另行明确要求发布或补跑某个指定案例，无需用户再重复创建资源或重新导入数据。
