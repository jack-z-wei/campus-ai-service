# TASK-028：AI 工程版网页展示场景补测与截图归档

- 日期：2026-10-08（Asia/Shanghai）
- 状态：已完成
- 范围：补充 Windows 真模型本地网页的可见功能场景和真实浏览器截图；不改变应用代码、默认端口服务或既有冻结评测结果。

## 运行方式与核验

- 使用 Windows 项目环境独立启动 API `127.0.0.1:8081` 与 Streamlit `127.0.0.1:8502`，隔离 SQLite 位于 `runs/ui-showcase-20261008/checkpoints.sqlite3`。
- 启动前配置探针返回 `USE_FAKE_MODEL=false`、模型 `deepseek-flash`、本地 DeepSeek Key 已配置；API health/info、UI health/page 均返回 HTTP 200。启动器未自动发起模型对话。
- 通过 Windows 可见 Chrome 浏览器，鼠标点击输入框，剪贴板粘贴，键盘回车，并对浏览器窗口执行 CopyFromScreen 截图。
- `runs/ui-showcase-20261008/api.log` 记录六个 `/campus-customer-service/stream` 请求均为 HTTP 200；页面接口不提供 provider token usage，因此本批调用的实际 token 与费用未知，不加入 `reports/API_USAGE.jsonl`。

## 实际场景

| 场景 | 输入与实际结果 | 截图 |
|---|---|---|
| 多轮追问 | 先问助学申请进度，系统追问编号；补充 `SIM-REC-001` 后返回“材料审核中”、更新时间 `2026-09-28 10:00` 和提交备注 | `submission/06_Demo/screenshots/engineering_ui_followup_20261008.png`、`engineering_ui_status_multiturn_20261008.png` |
| 多轮模拟服务单 | 针对该记录请求模拟工单；页面创建 `SIM-TICKET-4dceb292097e5718`，关联 `SIM-REC-001`、状态“已创建（模拟）”，并明确不会联系真人、不能确认真实处理时间 | `submission/06_Demo/screenshots/engineering_ui_simulated_ticket_20261008.png` |
| 未知问题拒答 | 询问图书馆当天各馆区开闭馆时间；页面指出抓取的官网快照不含公告正文，未编造具体时间并提供官网核验渠道 | `submission/06_Demo/screenshots/engineering_ui_unknown_hours_20261008.png` |
| 联系方式与来源 | 查询图书馆电话、邮箱；页面给出官网快照、URL 与 `2026-10-06` 抓取日期 | `submission/06_Demo/screenshots/engineering_ui_library_contact_20261008.png` |
| 校园政策与来源 | 查询每学期选课学分；页面回答一般 `15–35` 学分，超过 35（辅修专业超过 45）需要导师同意、学院审核、报教务处批准，并提示 2022 试行文件当前效力待复核 | `submission/06_Demo/screenshots/engineering_ui_course_credit_20261008.png` |

六张截图文件及 SHA-256、六条用户输入和逐场景观测摘要已记入 `runs/ui-showcase-20261008/manifest.json`。manifest 和输入文本副本归档在 `submission/04_Evaluation/runs/ui-showcase-20261008/`。

## 结果与边界

- 五类功能场景和六次用户输入有真实 Windows 页面结果；六张截图已插入 `reports/final_report.md` 与 `submission/05_Final_Report/final_report.md`。
- 状态与工单是项目本地课程合成数据，不是真实学生状态或学校客服工单。
- 页面未暴露实际 token usage 或账单金额；不对本批费用做估算。
- 独立测试服务在截图完成后停止。保留已有 8501 默认服务，不影响用户原有本地页面。

## 验收

- 六张截图与清单文件实际存在，报告链接检查无失效目标。
- 运行 manifest 确认真模型模式、独立端口和健康状态；API 日志与页面结果相符。
- 不把 UI 截图数量当成指导书的课程固定集案例数；冻结集仍以已有双路线评测记录为准。
