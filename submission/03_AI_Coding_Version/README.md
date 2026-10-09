# 长安大学校园智能客服助手：工程版

我把校园客服工程版整理成了可在 Windows 运行的交付包。浏览器界面连接 `campus-customer-service`，提供校园资料问答、合成状态查询和本地模拟服务登记。

## Windows PowerShell

```powershell
Set-Location <本目录的完整 Windows 路径>
uv sync --frozen
# 本地演示：API 与页面使用独立 SQLite，并打开默认浏览器
.\.venv\Scripts\python.exe scripts\launch_local_demo_windows.py
# 或手动分别启动 API 和 UI
.\.venv\Scripts\python.exe src\run_service.py
.\.venv\Scripts\streamlit.exe run src\streamlit_app.py
# 测试
.\.venv\Scripts\python.exe -m pytest tests\campus tests\app -q
```

运行时需要在本机配置模型服务；我没有把开发目录中的 `.env` 放入交付包。知识回答会显示检索来源；状态查询和工单只使用合成记录，不连接学校业务系统。请勿输入真实个人信息。

## 工程来源

我按课程项目需求改造了校园 Agent、检索流程、工具合同、合成数据、课程界面和评测材料。服务、消息协议及部分基础模块复用了一个公开的 MIT 项目；固定提交和文件级复用说明见 `UPSTREAM.md`，原始 LICENSE 保留。课程是否允许复用工程骨架仍待教师确认，我没有把它写成已获许可。
