# TASK-019：用户关闭后重新启动 FastAPI 后端

- 日期：2026-10-06（Asia/Shanghai）
- 状态：完成；后端进程运行中，前端未启动
- 验收目标：仅恢复 Windows 本地 FastAPI 服务，使用隔离 SQLite，确认健康端点和 Agent 清单可访问。

## 操作与结果

- 用户关闭了上一轮预览实例后，确认 8080/8501 空闲。本次通过 Windows 项目环境运行 `.\.venv\Scripts\python.exe scripts\launch_local_demo_windows.py --backend-only`，只启动 FastAPI。
- 当前实例：`runs/backend-preview-20261006-222643/`；PID `31684`；监听 `127.0.0.1:8080`。数据文件位于该 run 目录的 `checkpoints.sqlite3`，不会复用根目录 checkpoint。
- Windows PowerShell 对 `http://127.0.0.1:8080/health` 和 `/info` 的复核均为 HTTP 200；默认模型为 `deepseek-flash`，Agent 数量为 11。
- 本次没有发送聊天/模型请求，没有进行收费调用；`8501` 的 Streamlit 前端未启动。manifest 标记 `synthetic_data_only=true`、`course_result=false`、`paid_chat_performed_by_launcher=false`。

## 验收边界

- 后端 API 与 Agent 注册表已就绪；Swagger 页面为 `http://127.0.0.1:8080/docs`。
- 课程要求的浏览器 UI 现场查看和截图仍属 H-05 人工待办。如需 UI，须单独启动完整预览；当前 8501 页面不会打开。
- run manifest 和日志在上述隔离目录；实时 SQLite 和日志不进入提交包。
