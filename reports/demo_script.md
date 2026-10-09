# 校园智能客服演示脚本（Windows PowerShell）

## 演示前

1. 在 Windows PowerShell 进入项目目录：

   ```powershell
   Set-Location C:\Users\26313\Desktop\人工智能课设\campus-ai-service
   ```

2. 确认 `.venv`、本地 Ollama `bge-m3:latest` 和 `.env` 已在 Windows 配置。不要在终端回显 `.env`，也不要把 Key 放到截图中。
3. 推荐使用项目启动器启动 API、Streamlit 和隔离演示数据库，并自动打开浏览器：

   ```powershell
   .\.venv\Scripts\python.exe scripts\launch_local_demo_windows.py
   ```

   启动器将 API/前端限制在 `127.0.0.1`，设置 `deepseek-flash` 为默认模型，数据库写入新的 `runs/ui-preview-*` 目录。打开浏览器后，从 Settings 选择 `campus-customer-service` 和指定合成演示身份。

   如需手动启停，可使用下面的窗口一/窗口二方式；请先确认 `.env` 中的模型配置和数据库路径符合本次演示要求。

4. 手动启动 API（窗口一）：

   ```powershell
   .\.venv\Scripts\python.exe src\run_service.py
   ```

5. 手动启动 Streamlit（窗口二）：

   ```powershell
   .\.venv\Scripts\streamlit.exe run src\streamlit_app.py
   ```

6. 浏览器打开 `http://localhost:8501`。从 Settings 选择 `campus-customer-service`，并选择脚本指定的合成演示身份。仅展示模拟申请和工单，不输入真实学生信息。

## 固定演示

| 顺序 | 界面输入 | 合成身份 | 预期核对点 |
|---|---|---|---|
| 1. 知识与来源 | `长安大学本科生每学期修读多少学分比较合适？` | 任选演示身份 | 15–35 学分；答复引用 2022 试行文件并说明当前有效性待复核 |
| 2. 状态查询 | `我的宿舍维修单 SIM-REC-002 现在是什么状态？` | `SIM-USER-002` | 显示“已派单”及 2026-09-27 14:30，并明确是模拟数据 |
| 3. 多轮转人工 | 先问 `查一下我的宿舍报修单 SIM-REC-002。`，再问 `帮我转人工确认预计上门时间。` | `SIM-USER-002` | 第二轮记住上一轮记录并创建新的本地模拟工单；页面不能声称真人已联系 |
| 4. 未知问题 | `长安大学图书馆今天所有馆区具体几点开门、几点闭馆？` | 可选演示身份 | 不编具体时段；说明首页快照未提供该信息并建议核验官网 |

## 结果记录与限制

- 每题记录实际输入、模型显示值、回答、引用/工具结果、错误提示、运行日期和浏览器截图；失败也保留。
- 这份脚本列出可复现的演示场景；实际的 Windows 页面输入和截图记录在 TASK-028 中。截图用于说明页面功能，不作为课程现场演示记录。
- 工单只写入项目本地合成数据，不联系学校人工服务人员。新建工单可能写数据库；演示前如需清库，应先备份并按课程材料的可逆重建方法执行，不要直接删除原始评测数据库。
- 每次输入会向所选模型发起 API 请求并可能产生费用。离线评测和专用运行脚本会记录真实 usage；通用 `/invoke` 与 `/stream` 页面响应不含 provider token usage，因此普通界面请求无法估算单次费用，应以服务商账单为准。
- 使用启动器后，停止服务时按 `runs/ui-preview-*/manifest.json` 中的 PID 在 Windows PowerShell 执行 `Stop-Process -Id <api_pid>, <streamlit_pid>`；使用手动窗口启动时，在两个终端分别按 `Ctrl+C`。

## 2026-10-08 Windows 实际页面记录

这组证据来自单独的 Windows 本地实例：`deepseek-flash` 真模型，启动时核验 `USE_FAKE_MODEL=false`，独立 SQLite，浏览器由鼠标和键盘完成真实输入。五类功能场景共六次用户输入，六个 API `/stream` 请求均为 HTTP 200。状态与工单为合成数据。

| 场景 | 实际输入/交互 | 页面结果 | 截图 |
|---|---|---|---|
| 多轮追问 | `我想查询我的助学申请进度。` → `我的申请记录编号是 SIM-REC-001。` | 先询问缺失编号，再返回材料审核中的合成状态及更新时间 | `../submission/06_Demo/screenshots/engineering_ui_followup_20261008.png`、`../submission/06_Demo/screenshots/engineering_ui_status_multiturn_20261008.png` |
| 模拟转人工 | `请帮我为这条助学申请创建一个模拟人工服务单，咨询预计审核完成时间。` | 创建关联 SIM-REC-001 的模拟服务单；明确不联系真人、不承诺处理时间 | `../submission/06_Demo/screenshots/engineering_ui_simulated_ticket_20261008.png` |
| 未知问题 | `请问长安大学图书馆今天各馆区分别几点开门、几点闭馆？` | 不编造当天开放时段，指出官方快照缺公告正文并给出核验渠道 | `../submission/06_Demo/screenshots/engineering_ui_unknown_hours_20261008.png` |
| 来源问答 | `请问长安大学图书馆的联系电话和联系邮箱是什么？请给出资料来源。` | 返回官网快照中的联系方式、来源链接和抓取日期 | `../submission/06_Demo/screenshots/engineering_ui_library_contact_20261008.png` |
| 校园政策 | `长安大学本科生每学期修读的必修课和选修课学分一般以多少为宜？请说明超出后的要求并标明来源。` | 返回 15–35 学分范围、超出后的审批要求及政策来源 | `../submission/06_Demo/screenshots/engineering_ui_course_credit_20261008.png` |

启动配置、输入文本和逐场景观察记录见 `../submission/04_Evaluation/runs/ui-showcase-20261008/manifest.json`。页面响应不含 provider token usage，本次费用未知，不并入 `API_USAGE.jsonl`。
