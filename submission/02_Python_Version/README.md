# Python 原理版源码快照

这是我单独实现的 Python 原理版。演示入口使用显式 RAG 和 ToolRegistry CLI，不调用 LangGraph Agent。共用的配置和 schema 模块随源码附上；工程版在 `../03_AI_Coding_Version/`。

## Windows PowerShell

```powershell
Set-Location <本目录的完整 Windows 路径>
uv sync --frozen
# 先用本机 Ollama 做不收费的检索验证：
.\.venv\Scripts\python.exe scripts\run_campus_principles_windows.py `
  --question "长安大学本科生每学期修读多少学分比较合适？" --retrieval-only
# 真实 DeepSeek 聊天需在本目录本机 .env 配置自己的 Key；不要提交或分享该文件。
```

运行这一路线还需要本机 Ollama `bge-m3:latest`。固定来源、冻结用例、向量索引和本路线 traces 在本目录；工程版独立 traces 在兄弟工程包及 `../04_Evaluation/`。旧 trace 不能作为本次新运行结果。
