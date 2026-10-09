# Coze 校园智能客服配置与实测包

## 当前结果

截至 2026-10-07 的平台实测，Coze 个人空间中实际创建并运行了校园客服 Agent 草稿。知识库 A/B 各包含 14 份资料，界面显示 2,084 / 2,365 个分片；状态数据表导入 4 条合成数据；Agent 连接知识库 A 与两个个人空间工作流。状态查询与模拟工单工作流均有真实平台版本和合成数据运行记录。2026-10-08 已按实施文档 H-02 复核交付清单和材料索引。

指导书分类所需 14 个 Coze 案例、共 16 个助手轮次已运行并登记，满足计划中 Coze 技术交付的最低测试数量。还完成 A/B 知识库同题观察、Top-K/最低匹配度参数对照，以及 K01、S02 的三轨同题对照。结果表保留来源、实际回复、状态、偏差和截图位置；未从本地答案填充 Coze 输出。其中原始冻结结果有 5 条 partial，完整 21 题中没有在 Coze 运行的 7 题保持空白。

2026-10-08 按实测缺陷修订了知识来源/时效披露提示词，并在 Coze 草稿自动保存后从页面复制回项目文件逐字核对。随后按原冻结题面补跑 K01、K06、K09 三题，未覆盖原始结果：K09 新回答明确披露 2017-10-26 日期、来源链接、适用对象及当前效力未确认，补充复测通过；K01 因检索片段未提供日期仍为 partial，K06 未说明目录与正文日期冲突及当前效力，仍为 partial。实际输出和截图见 `retests/20261008/` 与 `screenshots/rerun_20261008_*.png`。Agent 仍为草稿，没有点击发布。

Agent 仍为草稿，未公开发布。Coze 没有提供完整的每轮 workflow 参数与调用 trace、实际账单或 embedding 单价。身份编号是提示中提供的合成测试值，不是账号认证。模拟工单不通知真实人员。以上限制已保留在报告和实测日志中。

## 目录

- knowledge/：14 份校园资料快照。
- source_manifest.csv：来源 ID、URL、日期、适用范围和 SHA-256。
- instructions.txt：2026-10-08 已保存并与平台复制文本逐字一致的提示词；修改前快照见 logs/platform-prompt-snapshot-20261008.txt。
- workflow/：合成表格数据、字段合同、配置计划及状态查询设计图。
- evaluation_minimum_cases.json：选取的 14 题 / 16 助手轮次。
- results.csv：逐题真实 Coze 输出、状态、偏差和截图路径。
- retests/20261008/：不覆盖冻结基线的三条提示词修订后同题复测记录。
- experiment_sheet.csv：A/B 两组资料处理结果和同题观察。
- retrieval_parameter_comparison.csv：Top-K 与最低匹配度的实测对照。
- logs/agent-evaluation-20261007.md：实测配置、运行范围和限制。
- screenshots/：知识库、数据库、工作流、Agent 运行和对照截图。
- 用户操作说明.md：当前 Coze 结果、限制和范围说明。
- 验收补齐清单.md：按模块登记完成证据与限制。
- 截图清单.md：报告可用截图索引。

Coze H-02 技术交付清单已具备对应配置、运行和截图证据；平台执行不等于教师签收或公开发布。账户账单、余额和真实收费状态没有在页面中看到，因此不填写费用结论。Agent 仍是未公开草稿；指导书要求建立、运行和留存真实 Bot 结果，未要求公开发布。

参考资料： [知识库分段](https://docs.coze.cn/guides_knowledge_base_segmentation)、[工作流](https://docs.coze.cn/guides_workflow)、[数据库](https://docs.coze.cn/guides_database)、[数据库查询节点](https://docs.coze.cn/guides_database_select_node)、[数据库新增节点](https://docs.coze.cn/guides_database_insert_node)、[计费说明](https://docs.coze.cn/coze_pro_billing_faq)。公开文档不等于账号当前功能或计费状态。
