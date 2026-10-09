# 校园知识来源与使用边界

本目录的 `source_manifest.json` 是知识资料唯一来源清单，记录 14 个长安大学官方页面或 PDF 的原始文件、SHA-256、抓取时间、发布日期/HTTP `Last-Modified`、主题、适用范围及提取文本。来源覆盖教务、奖助、宿舍和图书馆四类。

`raw/` 保留下载原件；同名 `.md` 是 UTF-8 文本快照。当前主页是动态站点，`library_home_2026.md` 是人工核对摘要，配套原始 HTML 和服务端渲染文件保存在 `raw/`。摘要只提取官网联系方式、服务入口和公告标题日期，不含公告正文，因此不能回答当前开放时段。

## 版本与索引约束

- `dated_policy`：只按文件注明年份回答，说明年份；不得暗示该文件当前仍有效。
- `time_limited_notice`：只能回答对应学期/假期的事项，不外推到其他时间。
- `historical_policy`、`narrow_scope_historical`：明确适用对象和年份；当前效力未核实的现行问题应建议查询主管部门。
- `version_conflict_review_required`：公告目录标注 2025 年，但 PDF 正文落款为 2016 年；不得把它当作现行规定回答。
- `archive_not_for_current_answers`：旧版图书馆页面已由官网标作“回忆旧版”，不用于当前开放时间、借阅或校外访问答案。
- `current_homepage_snapshot`：可回答页面明确显示的联系电话、邮箱、服务导航与公告标题；不从标题推测公告细节。

校园知识库只收录来源清单登记的公开资料。个人成绩、宿舍、申请进度和服务工单全部使用 `data/campus/simulation_records.json` 中的合成演示记录；标识以 `SIM-` 开头，不对应真实学生。
