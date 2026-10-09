# Coze 校园智能客服配置与实测包

## 当前结果

我于 2026-10-07 在 Coze 个人空间创建并运行了校园客服 Agent 草稿。知识库 A、B 各有 14 份资料，页面显示 2,084 和 2,365 个分片；状态表中有 4 条合成记录。Agent 连接知识库 A 和两个工作流，状态查询与模拟工单都留有平台运行记录。2026-10-08 我又按实施文档 H-02 核对了交付材料。

我实际运行并登记了 14 个 Coze 案例、共 16 个助手轮次，也比较了 A/B 知识库、Top-K/最低匹配度参数，以及 K01、S02 的三条路线输出。结果表记录了来源、平台回答、判定、偏差和截图；Coze 输出没有用本地答案补写。原始结果中有 5 条 partial；21 题冻结集里有 7 题没有在 Coze 运行，结果栏保持空白。

2026-10-08，我根据实际回答中出现的问题补充了知识来源和时效说明，并把 Coze 自动保存的提示词复制回项目文件逐字核对。随后按原题面重跑 K01、K06、K09，没有覆盖旧结果。K09 补上了 2017-10-26 日期、来源链接、适用对象和当前效力说明，本次复测通过；K01 的检索片段没有日期，K06 没有说明目录与正文日期差异及当前效力，两题仍为 partial。输出和截图见 retests/20261008/、screenshots/rerun_20261008_*.png。Agent 仍是草稿，我没有发布它。

Coze 没有提供完整的逐轮 workflow 参数、调用 trace、实际账单或 embedding 单价。测试中使用的身份编号是合成值，不代表账号认证；模拟工单也不会通知真实人员。我把这些限制保留在报告和实测记录中。

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

按 H-02 清单整理后，Coze 配置、运行和截图材料都已归档。页面没有显示账号账单、余额或实际收费情况，因此我没有填写费用结论。Agent 仍是未公开草稿；本次材料记录的是平台实测，不代表教师签收或公开发布。

参考资料： [知识库分段](https://docs.coze.cn/guides_knowledge_base_segmentation)、[工作流](https://docs.coze.cn/guides_workflow)、[数据库](https://docs.coze.cn/guides_database)、[数据库查询节点](https://docs.coze.cn/guides_database_select_node)、[数据库新增节点](https://docs.coze.cn/guides_database_insert_node)、[计费说明](https://docs.coze.cn/coze_pro_billing_faq)。公开文档不等于账号当前功能或计费状态。
