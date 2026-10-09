# TASK-001：Windows 环境与依赖

- 日期：2026-10-06（Asia/Shanghai）
- 状态：已完成（本机环境验收）；云端密钥实验待 H-01
- 目标：记录真实 Windows Python、项目 venv、上游依赖和 BGE 推理；区分本机服务成功与云端 API 待人工。
- 范围：本项目目录、Windows Python 3.12 venv、Windows uv、Ollama 本地接口；不改全局 Python 包或系统配置。

## 验收条件

1. Windows 项目 venv 启动，记录 `sys.executable`、`sys.platform`、Python 版本。
2. 上游锁定依赖在 Windows venv 安装成功；若 Windows wheel/依赖失败，保留完整错误并处理。
3. Ollama `/api/embed` 对实际文本返回非空向量，输出维度以推理结果为准。
4. 检查 `.env` 是否存在非空 Key，但不显示、复制或记录 Key 内容；未配置 Key 时标记云端实验待人工，不阻塞本机验收。
5. 有脱敏环境报告和依赖同步日志；不以 WSL 解释器结果代替。

## 已执行

- Windows venv 实际解释器为 `C:\Users\26313\Desktop\人工智能课设\campus-ai-service\.venv\Scripts\python.exe`，`sys.platform=win32`、Python 3.12.7。
- `uv sync --frozen` 成功，依赖日志保存在 `reports/dependency_sync.log`。
- Ollama `/api/tags` 确认 `bge-m3:latest`；Windows 实际 `/api/embed` 返回 1 条、1024 维有限值向量。
- `.env` 存在但 `DEEPSEEK_API_KEY` 未配置；检查结果只记录布尔值，不读取或显示密钥。
- Windows 定向测试：37 passed；上游全量测试：194 passed、4 skipped、18 warnings。4 项需 Docker，未运行。
- fake model 服务到 Streamlit 烟测成功，见 `runs/smoke-20261006-164758/manifest.json`；不作为课程问答结果。

## 文件 / 证据

- 环境检查脚本：`scripts/check_windows_environment.py`
- Windows 环境 JSON：`reports/WINDOWS_ENVIRONMENT.json`
- 依赖日志：`reports/dependency_sync.log`
- 服务/UI 烟测：`scripts/smoke_template_windows.py`，成功记录在对应 smoke manifest。

## 失败与修复

- 初次在 WSL interop 中直接嵌套 Python `-c` 的引号导致命令文本被错误转义；后续改用项目内 `.py` 文件由 Windows Python 执行，避免在终端显示或转义密钥。
- 首次全量测试中，Windows Streamlit worker 因测试 fixture 清空 `USERPROFILE` 超时；fixture 已修改为保留平台 home 环境变量，复跑通过。首次失败日志未单独保存。
- 烟测前两次失败：脚本导入路径、Streamlit toolbar 自动 rerun；修正后第三次端到端通过。所有三份 manifest 均保留，成功烟测标记为 fake / 非课程结果。

## 用户参与

- 不需用户安装全局依赖。H-01 API Key 独立记录，不阻塞资料整理、向量索引和无密钥测试。
