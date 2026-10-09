# TASK-014：Coze 实测与三轨对照准备

- 日期：2026-10-06（Asia/Shanghai）
- 状态：进行中（Coze A/B 知识库已上传；两张数据库表已由用户确认创建，状态表已导入 4 条模拟记录；智能体草稿与知识库 A 已连接；K01 已有一次真实平台输出；当前用户只要求准备报告所需截图）
- 对照用例：冻结集 K01 知识问答、S02 带合成身份和明确宿舍维修参数的状态查询。

## 已完成的可自动工作

- 创建 `reports/Coze_Python_Engineering_Mapping.md`，逐项映射资料、切分、Embedding、检索、提示词、状态查询、模拟工单、多轮和原始 trace，清楚标注 Coze 对应行为尚未实测。
- 添加 Windows 脚本 `scripts/prepare_three_track_comparison_windows.py`。它从 TASK-013 的优化版 parent index、manifest 和逐例 trace 抽取四条本地真实模型结果，不复制文本、不发新 API 请求，并为 Coze 留出两条明确待填记录。
- 在 Windows 项目 `.venv` 运行脚本生成 `reports/three_track_comparison.csv`：6 行（两道题 × 三条路线），本地完成 4 行、Coze 待平台实测 2 行。脚本断言两道题的本地记录均有已完成运行和原始回答，Coze 两行必须保持空白且状态为“待平台实测”。
- K01 及 S02 的三路线原题和 `SIM-USER-002` 合成身份与 `coze/test_cases.md`/冻结集一致。每行含模型、Prompt/source/frozen SHA-256、答案、检索来源或工具调用/参数/结果、延迟口径、运行 ID 和证据路径。
- 脚本 Windows `ruff check` 与 `py_compile` 通过；Windows Python 重新读取生成的 UTF-8 CSV，确认 6 行、三种 route 和四份非空本地答案。第一次验证误用了 WSL `python` 命令（该环境没有该命令）；已改用项目 Windows Python 完成，不将 WSL 命令失败算作项目失败。

## 原始本地行

| 用例 | Python 原理版 | LangGraph 工程版 |
|---|---|---|
| K01 | `principles-20261006-194536-9c9d3f61` | `engineering-case-20261006-195101-09c7e8bb` |
| S02 | `principles-20261006-194813-2443168e` | `engineering-case-20261006-195403-214f8dc5` |

四行的具体答案、调用、usage 和 timing 取自 `runs/` 对应原始 manifest/trace。Principles 时间按检索加 provider round-trip；Engineering 按 LangGraph `ainvoke` 完整墙钟测量，不能把跨路线时间差解释为性能对照结论。

## Coze 平台进展（2026-10-07）

- 用户在个人空间创建了 `校园客服知识库-A` 和 `校园客服知识库-B`，截图可见两库各 14 份文档，均为自定义分段；A 为 2,084 个分片，B 为 2,365 个分片；两库大小均约 141.68 KB，当前命中数均为 0（尚未运行问答测试）。
- 按实际 UI 能力，将候选分隔符调整为单一规则：A 用两个连续换行、500 字符、16% 重叠；B 用单个换行、700 字符、0% 重叠；两组快速解析、预处理关闭、平台共享存储。`coze/experiment_sheet.csv` 已记下实际设置和分片数。
- 当前聊天截图确认文件数与分片数，但未显示配置参数页；平台截图尚未保存到项目 `coze/screenshots/`，后续需补存 A/B 参数页和知识库总览作为交付证据。
- 用户已创建扣子数据库 `application_status` 并保存表结构。截图确认保留系统字段 `id`、`sys_platform`、`uuid`、`bstudio_create_time`；添加了 7 个业务字段：`record_id`、`owner_sim_user_id`、`service_type`、`status`、`updated_at`、`public_note`、`simulation_only`，类型与本地 schema 一致，均设为必要字段；查询模式为单用户、渠道模式为隔离。用户确认已导入 4 条测试记录且全部 `simulation_only=true`；Coze 生成的 `uuid` 是系统字段，不能用作 `SIM-USER-###`。
- 用户进入“测试数据 > 批量导入”后，界面强制弹出“请选择导入渠道”，列表未见明确写作“扣子编程”的选项；随后进入批量导入向导并上传了 `coze/workflow/application_status_coze_import.csv`。已下载平台模板并保存副本为 `coze/workflow/coze_application_status_template.xlsx`；核对其 A:G 列头与本地数据完全一致，模板第二行 `simulation_only=false` 是默认示例值。首次第 2 步出现“参数校验未通过，字段名称不匹配”；去掉 CSV UTF-8 BOM 后重传，字段错误消失，预览显示 SIM-REC-001..004 四行。用户确认四行 `simulation_only=true` 并完成导入。平台数据表的最终截图未保存到本地，完成状态基于用户确认；数据库表查询仍未在工作流中实测。渠道列表与官方关于测试数据默认扣子编程渠道的说明存在差异，实际选择渠道待在证据材料中按 UI 可见名称注明。

## 仍待 H-02 平台实测

- Coze 个人空间和 A/B 知识库已实际创建并处理文件；K01 已有一次真实平台部分通过输出，模型/Embedding 价格及账单仍未核验。`coze/package_manifest.json` 保持 `prepared_not_platform_tested`，因为工作流和端到端测试未完成。
- 已建立 `application_status` 表并导入 4 条用户确认的合成状态记录；用户随后确认已创建 `human_service_ticket` 表，但尚无字段结构截图核验。数据库查询/新增节点、失败输出和自动字段仍待实测。
- 用户截图确认 Coze 智能体草稿为 `长安大学校园智能客服`，模式是“单 Agent（自主规划模式）”，模型显示“豆包·2.0·pro”；后续截图显示知识库 A 已挂载、知识提示词已填写并在预览运行 K01。回答包含“15 至 35 学分为宜”及来源标题，核心事实符合预期；预览同时显示冗长思考内容，最终答复未写来源年份/日期并增加审批细节。初次结果记入 `coze/results.csv` 和 `coze/logs/K01-20261007-initial.md`；K01 截图已从用户提供的 Windows 目录逐字节复制至 `coze/screenshots/03_Agent与K01.png`。来源 ID、运行 ID 和耗时不可见；三轨 CSV 的 Coze/K01 行记录为部分通过。
- 已收紧 `coze/instructions_agent_knowledge_smoke_test.txt`，供未来完整 Coze 测试时使用；当前用户仅要求报告截图，故不要求将该提示词再贴入 Coze或重复运行 K01。
- 用户明确缩小当前目标为“只需要交报告需要的截图”。报告模板 12.1 有 3 个 Coze 结构截图位，24.1 有 1 个最终 Coze 界面截图位；没有要求为了截图跑完整 21 例 Coze 冻结集。停止要求重复 K01 或批量测试，优先整理已提供的知识库/Agent/K01 实际画面。指导书的 Coze 五问练习与完整数据库/工作流验收仍不能因此标成已完成。
- 已从 `C:\Users\26313\Pictures\Screenshots` 精选并原样复制知识库 A/B、`application_status` 表结构/测试行、Agent+K01 共 5 张截图至 `coze/screenshots/`；源图哈希与副本一致，源目录原图未改动。清单和最终报告 Coze 截图段落据此更新。
- 用户已授权不设 API 费用上限并明确允许付费模型。执行收费调用前仍记录平台展示的模型/Embedding 价格或额度，不再把等待用户设置预算作为阻塞；工作空间、分段字段及数据库节点能力仍需按实测记录。
- 若以后恢复完整三轨验收，再在真实 Coze 界面运行 CSV 中 K01、S02，并回填实际来源、参数、结果与可见耗时；当前用户未要求此项。
- 完整三轨通过条件仍为 K01/S02 均有独立 Coze 证据、总计至少 6 份真实输出；当前仅完成截图交付范围，不将此完整标准标成通过。

## 2026-10-07 后续状态

本任务正文中的“仍待平台实测”描述的是 TASK-014 当时的状态，现已由 TASK-024 接续：Coze 14题/16轮、两个工作流、A/B/检索参数观察和 K01/S02 三轨真实输出已归档。Agent 未公开发布；账单与部分逐轮 trace 仍不可见。
