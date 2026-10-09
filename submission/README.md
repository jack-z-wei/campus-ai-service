# 校园智能客服课程设计交付包

## 六类目录

1. `01_Coze_Version/`：Coze 知识库、模拟状态表、两个个人空间工作流及 Agent 草稿；H-02 技术交付项已具备真实配置、14 题/16 助手轮次与对照证据。原始冻结结果 5 条 partial 仍保留；提示词修订后另有 3 条复测（1 条通过、2 条 partial），原结果未覆盖。平台不可观测字段如实保留；Agent 未公开发布。
2. `02_Python_Version/`：独立 Python 显式 RAG/ToolRegistry 源码、依赖锁、来源、向量索引和 Principles 路线结果。
3. `03_AI_Coding_Version/`：长安大学校园客服 LangGraph/FastAPI/Streamlit 工程版、测试、依赖和 Engineering 路线结果；工程来源在 `UPSTREAM.md` 公开记录。
4. `04_Evaluation/`：冻结集、全部原始 runs/traces、指标、Judge、失败、用量与评分表。
5. `05_Final_Report/`：31 章课程设计报告、图表、范围说明。
6. `06_Demo/`：Windows 演示脚本和本地页面测试截图，便于查看界面并复现演示场景。

我把课程设计交付材料整理为上面的六部分。报告已填写课程、学生、学号和指导教师信息，班级未提供。V1、V2 各有 5 份回答，统一 Rubric 评分均为 30/30；评分表记录了 Codex 评分者、分项理由和 trace。K01、K10、U02 三个检索问题都有失败记录，其中 K01 和 K10 已修复，U02 仍未解决。交付包只说明技术材料和运行证据，不代表教师签收、公开部署、现场演示或课程平台提交。

## 安全与复现

- 包内不包含 `.env`、`.venv`、`.git` 或 Python cache。`.env.example` 只含空配置字段；需要运行真实聊天时，在各路线本机单独安全配置。
- `.venv` 不打包；从各版根目录在 Windows PowerShell 按 README 用对应 `uv.lock`/`uv sync --frozen` 安装。
- 两条本地路线的安装/种子索引/启动方式各自记录；模型实时调用会计费。通用 UI 的 `/invoke` 响应不含 provider token usage，单次 UI 调用成本需查看服务商账单。Evaluation 离线重算使用已保存 trace。
- UI preview 的静态 manifest/AppTest 记录可供审阅；仍在运行的预览数据库和日志不打包。
- `package_manifest.json` 记录了交付文件的 SHA-256。若之后修改评分、Coze 运行记录或截图，需要重新生成并核对清单。
