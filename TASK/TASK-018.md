# TASK-018：打开 Windows 前端并完成真实模型功能测试

- 日期：2026-10-06（Asia/Shanghai）
- 状态：前端已打开；自动 API/UI 检查与一条合成身份真实模型问答通过；浏览器视觉检查与截图待用户
- 验收目标：在 Windows 原生项目环境启动 Streamlit 前端和 FastAPI 服务，验证校园 Agent、`deepseek-flash` 与状态工具链路，并给用户留下可现场查看的页面。

## 前端位置与当前运行实例

- Streamlit 入口：`src/streamlit_app.py`。
- 本地页面：`http://127.0.0.1:8501`；FastAPI：`http://127.0.0.1:8080`。
- 使用 Windows 项目 `.venv` 执行 `scripts/launch_local_demo_windows.py`。启动器在 Windows Python 子进程环境中明确设定 `USE_FAKE_MODEL=false`、`DEFAULT_MODEL=deepseek-flash`、localhost 绑定和 run 专属绝对 SQLite 路径，然后检查 API、Agent 清单、Streamlit 首页/健康端点，并打开 Windows 默认浏览器。
- 当前实例 run ID：`ui-preview-20261006-210701`；PID 记录、健康码和设置见 `runs/ui-preview-20261006-210701/manifest.json`。SQLite 位于该 run 目录。启动器没有发送聊天请求；本地服务保持运行供 H-05 查看。

## 测试结果

- Windows 启动器 Ruff 和 `py_compile` 检查通过。
- 启动器验证 FastAPI `/health` 和 `/info` 为 200，`/info` 默认模型为 `deepseek-flash` 且列出 11 个 Agent；Streamlit `/` 与 `/_stcore/health` 均为 200；Windows 默认浏览器打开成功。
- Streamlit `AppTest` 选择 `campus-customer-service`、`deepseek-flash` 和合成身份 `SIM-USER-001`，经运行中的 FastAPI 发出一条真实模型请求。UI 显示 `SIM-REC-001` 的合成状态“材料审核中”、更新时间和公开备注。结果为真实 DeepSeek 回复，不是 fake 输出，也不是人工评分或冻结集课程结果；证据 `runs/ui-preview-20261006-2105/live-ui-app-test.json`。
- DeepSeek 服务的 `/invoke` 响应不包含 token usage。此 UI 请求的模型 invocation 数、token 数和费用无法从现有 API 响应确定；没有估算或写入虚构 usage。故 20:50 的 275 条 usage 统计未包含这一条 UI 请求，其真实费用未知。
- 调试时发现 WSL shell 变量没有传入 Windows Python 进程，第一次测试因 `.env` 默认值返回 fake。之后显式选 `deepseek-flash` 完成真实 UI 测试，确认根目录数据库新增的两个测试 thread 均由本次 synthetic smoke 创建；按精确 thread ID 删除这两条测试记录，保留其余 checkpoint。根 `checkpoints.db` 完整性检查为 `ok`，大小恢复为原有 53,248 bytes。当前长期实例由修正后的 Windows 启动器启动，使用独立 SQLite，根 DB 不被实例访问。
- Docker CLI / daemon / Compose 配置已在 TASK-017 核验；这次 SQLite 本地路线不需要启动容器。

## 提交材料复核

- TASK-018、启动器、静态运行 manifest、真实 UI 测试记录、演示说明和报告已同步入六类提交包。
- Windows manifest refresh 后共 6 个交付目录、1,157 个文件；逐文件 SHA-256 复核无不匹配，未发现 `.env`、`.venv`、缓存目录或常见 API key 格式。根报告和提交版报告各 10 个本地 Markdown 链接全部有效。
- 仍运行的 UI preview SQLite 与日志不复制到提交包；只同步静态 manifest 和测试结果。

## 人工待办与验收边界

- H-05：请用户查看已打开的浏览器，确认页面可读，并在左侧 Settings 选择校园 Agent 及合成演示身份；需要提交的截图由用户保存至 `submission/06_Demo/screenshots/`。自动 AppTest 不代替现场视觉验收。
- 运行中的实例绑定 `127.0.0.1`，使用 `deepseek-flash`；通过 UI 继续提问会产生新的真实模型费用。其服务响应当前不暴露 usage，需以服务商账单核对实际费用。
- 未启动 Docker/Compose；未用真实学生信息或真实学校业务系统。
