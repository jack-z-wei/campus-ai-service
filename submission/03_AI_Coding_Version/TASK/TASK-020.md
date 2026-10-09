# TASK-020：连接现有后端并启动 Windows 前端

- 日期：2026-10-06（Asia/Shanghai）
- 状态：自动启动与 HTTP 验证完成；浏览器视觉检查和截图待用户
- 验收目标：在不重启 API 的前提下启动 Streamlit，连接 TASK-019 的 FastAPI，并打开本地页面。

## 操作与结果

- 先确认现有 API 的 `/health`、`/info` 可用，再用 Windows 项目 `.venv` 运行 `scripts\launch_local_demo_windows.py --ui-only`。启动器只创建 Streamlit 子进程，连接 `http://127.0.0.1:8080` 上已运行的 API。
- 前端实例：`runs/ui-preview-20261006-230144/`；Streamlit PID `15700`；页面 `http://127.0.0.1:8501`。Windows 默认浏览器打开成功，`/_stcore/health` 与 `/` 均返回 HTTP 200。
- 后端仍是 TASK-019 的 PID `31684`；`/health` 与 `/info` 返回 HTTP 200，默认模型 `deepseek-flash`，11 个 Agent。前端没有另起 API，也不拥有新的 SQLite 数据库。
- 本次启动和 HTTP 检查没有发送聊天/模型请求，没有进行收费调用；manifest 标记 `attached_to_existing_api=true`、`api_started_by_launcher=false`、`paid_chat_performed_by_launcher=false`。

## 验收边界

- UI 已在 Windows 浏览器打开，但自动检查只覆盖页面 shell 和健康端点。H-05 仍需用户本人查看页面内容、进行课程演示并保存截图；不把 HTTP 200 当作视觉验收。
- 当前 API 和 Streamlit 都只绑定 localhost。API 使用 TASK-019 隔离运行目录中的 SQLite；不要把运行日志或活动数据库复制进提交包。
