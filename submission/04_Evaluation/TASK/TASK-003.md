# TASK-003：官方校园资料与隔离的演示数据

- 日期：2026-10-06（Asia/Shanghai）
- 状态：已完成（资料采集与版本审查）；后续索引由 TASK-005 执行
- 目标：收集不少于 10 份官方校园资料，确认原文件、主题、日期、适用范围和文本提取质量；将演示业务记录与真实校园资料隔离。
- 范围：长安大学官网、教务处、学工部和图书馆公开来源；不使用用户的课程报告作知识文档，不抓取学生公示名单或真实个人状态。

## 验收条件

1. 至少 10 份公开官方资料，覆盖至少 2 类，优先覆盖教务、奖助、宿舍和图书馆。
2. 每份来源有 URL、原始文件、SHA-256、抓取时间、主题及适用范围；PDF 保留可核验原件和文本快照。
3. 老政策、季节通知、范围受限规定和无法确认现行效力的资料显式标记，不冒充当前政策。
4. 业务状态种子全部为合成数据，不含真实学生身份或账号状态。

## 已执行

- Windows 运行 `scripts/acquire_campus_sources.py`，14/14 个官方页面/PDF 获取成功，来源覆盖教务、奖助、宿舍、图书馆四类。
- 生成原件、UTF-8 文本快照和 `source_manifest.json`；清单记录 SHA-256、HTTP `Last-Modified`、文本字符数和来源版本策略。
- 使用 Windows `pypdf` 提取 PDF 文本。对照 PDF 正文修正了两处初始元数据：本科生学籍规定的实际版次是 2022 版；《学生管理规定》正文落款为 2017 年。
- 发现勤工助学管理办法公告目录标注 2025-08-03，但 PDF 正文落款 2016-07-08、HTTP `Last-Modified` 为 2021-07-07；标记版本冲突，不能用于现行政策结论。
- 图书馆当前主页采用动态页面，保留原始 HTML/渲染快照和只包含主页可见事实的人工核对摘要；当前时段不从公告标题推断。旧版读者须知、开放时间和校外访问页面保留为历史来源，不用于回答现行规则。
- 创建 `simulation_records.json`，共 4 条 `SIM-` 合成业务记录，明确不是实际学生记录。
- Windows 来源完整性检查：14 sources、4 categories、0 errors；全部原件 hash 匹配、文本快照无 Unicode replacement character。

## 文件 / 证据

- 来源目录：`docs/campus/source_manifest.json`
- 原始文件与文本快照：`docs/campus/raw/`、`docs/campus/*.md`
- 索引与时效边界：`docs/campus/README.md`
- 模拟业务记录：`data/campus/simulation_records.json`
- 采集脚本：`scripts/acquire_campus_sources.py`
- 完整性检查：`scripts/check_campus_sources.py`

## 失败与修复

- 第一轮 HTML 提取使用了响应头的错误默认编码，发现目录正文出现 mojibake。改为优先按 HTTP charset 和 HTML meta charset 解码后重抓，UTF-8 检查通过。
- 首轮元数据根据文件 URL/目录标注误写了一份学生管理规定年份；由 PDF 正文校正为 2017 年。错误快照仍作为未纳入 manifest 的工作记录保留，当前知识库加载器必须以 `source_manifest.json` 为准；清理待用户确认验收后执行。

## 未解决事项

- 2022 本科教务规则、2017 学生管理规定、2012 消防规定、2021 助学金文件以及旧版图书馆页面的现行效力或适用性尚未由主管部门确认。回答现行问题时应拒绝从这些材料外推。
- 下一任务 TASK-004 冻结 21 个测试用例；实现 Loader 时仅读取 manifest 登记的 `.md`，避免读取错误快照及模板内置非校园样例。
