我整理了以下 Windows 本地网页的浏览器交互截图。助学记录和工单都是合成数据，页面没有输入真实学生信息；这些截图记录的是页面测试，不代表我已完成课程现场演示。

- `campus_ui_home.png`：校园客服首页
- `engineering_ui_home_20261008.png`：工程版首页
- `engineering_ui_status_20261008.png`：工程版公开政策与合成状态
- `engineering_ui_followup_20261008.png`：多轮第一轮，缺少申请编号时先追问
- `engineering_ui_status_multiturn_20261008.png`：多轮第二轮，按编号查询合成状态
- `engineering_ui_simulated_ticket_20261008.png`：多轮第三轮，创建本地模拟工单并说明不会联系真人
- `engineering_ui_unknown_hours_20261008.png`：当前开放时间未知时拒答并给出官网核验渠道
- `engineering_ui_library_contact_20261008.png`：图书馆联系电话、邮箱与官方来源
- `engineering_ui_course_credit_20261008.png`：选课学分范围、超出要求和来源文件

六张新增截图来自 Windows 独立的 `deepseek-flash` 真模型运行，启动时确认 `USE_FAKE_MODEL=false`，并使用独立 SQLite。运行 manifest、六条输入和逐场景观察见 `../04_Evaluation/runs/ui-showcase-20261008/`。本地 `/stream` 响应没有返回 token usage，因此无法从响应核算这次调用费用。
