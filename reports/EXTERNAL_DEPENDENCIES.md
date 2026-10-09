# 外部依赖与运行条件

更新时间：2026-10-08（Asia/Shanghai）。我在这份记录中汇总了项目运行依赖、平台状态和目前无法核实的信息；Coze 提示词修订及三条补充复测已完成。

| 项目 | 当前状态 | 依据 / 下一步 | 对任务的影响 |
|---|---|---|---|
| Windows Python | 已验收：项目 `.venv` 使用 `C:\ProgramData\anaconda3\python.exe` 创建，运行时 `sys.executable` 指向 `.venv\Scripts\python.exe`，Python 3.12.7、`win32` | 证据：`WINDOWS_ENVIRONMENT.json` | 满足上游 `>=3.12,<3.15` |
| Windows Git / uv | 已验收：Windows Git、uv；`uv sync --frozen` 成功 | 同步日志：`dependency_sync.log` | 依赖位于项目 `.venv`，未安装全局 Python 包 |
| Ollama | 已验收：Windows 本机 `127.0.0.1:11434` 可访问，`bge-m3:latest` | `/api/tags` 元数据维度 1024；实际 `/api/embed` 返回 1 条、1024 维有限值向量 | 本地、无 API 费用 |
| DeepSeek API | 官方模型名 `deepseek-flash`，OpenAI 兼容地址 `https://api.deepseek.com`，官方文档列出 Tool Calls | Windows 配置已适配，Key 位于被 Git 忽略的 `.env`；真实连通、状态 Tool Calling、RAG 和 Prompt 批次均已运行 | 密钥值不写入报告、运行清单或 Git |
| DeepSeek 预算 | 用户已取消金额上限 | 调用限定在课程任务内并分批执行，限制单次输出且不自动重试；可见 provider usage 的专用实验写入模型、usage 与费用估算 | 通用 UI `/invoke` 当前不返回 provider usage，UI 请求费用需标为未知；账号余额和实际账单未知 |
| DeepSeek 单价与用量 | 用户已取消总预算金额上限；截至 2026-10-06 18:45 共 49 次模型回复 | 官方价格页标注 `deepseek-flash` 当前对应 DeepSeek-V4.1-Flash。峰时输入缓存未命中 US$0.30/百万 token、缓存命中 US$0.006/百万 token、输出 US$1.20/百万 token；非峰时半价。累计 usage 输入 109,734、输出 6,911 tokens；按峰时、全部输入缓存未命中估算 US$0.0413181。首个请求 usage 和单位更正见 `API_USAGE_ADJUSTMENTS.jsonl`。 | 早期 thinking 开启、请求 `max_tokens=32` 时服务端返回 75 output tokens；后续关闭 thinking、设置 768 的实际 usage 未超过该配置，但不据此宣称普遍硬上限。可见 usage 的专用实验记录于 `API_USAGE.jsonl` 和各 run manifest；TASK-018 UI 请求无法量化。Coze 平台费用不包含在 DeepSeek API 用量中 |
| Coze | 2026-10-07 核验个人空间、Bot、知识库、数据表和两个工作流；2026-10-08 修订并核对草稿提示词、同题复跑3题。真实余额、收费记录及 embedding 单价不可见 | 原始固定集14题/16轮、A/B分段、检索参数及三轨同题结果；补充复测3题（K09通过，K01/K06仍partial）均已归档。H-02技术清单见 `coze/验收补齐清单.md` | 平台实测不是教师签收；Agent 未公开发布；原始冻结结果5条partial、7个冻结题未在Coze执行均有披露。补测独立记录、不覆盖基线；实际账单及部分trace不可观测 |
| 上游工程模板 | 已固定当前 `main` 提交 `88ebfa1fadd1a207aa92115635abf7ed20d66a88`，MIT | `UPSTREAM.md` 记录 URL、许可、复用范围；原课程选型材料提示是否准许完整模板底座需教师答复 | 开源许可可依其条款使用；课程验收接受度待确认 |
| 模型密钥 / 账号状态 | DeepSeek Key 已配置且实测；账号余额/充值状态未核验；Coze 已在个人空间实测但余额未知 | DeepSeek Key 只保存在 Windows 本地 `.env`；不得输出、提交或写入报告 | DeepSeek 已用于已授权课设调用；Coze 平台账单与余额仍不可见 |

## 官方资料

- DeepSeek 模型和价格：<https://api-docs.deepseek.com/zh-cn/quick_start/pricing/>
- DeepSeek 思考模式及关闭方式：<https://api-docs.deepseek.com/guides/thinking_mode/>
- DeepSeek V4.1-Flash 更新：<https://api-docs.deepseek.com/zh-cn/news/news260910/>
- DeepSeek Tool Calls：<https://api-docs.deepseek.com/zh-cn/guides/tool_calls/>
- Coze 工作流节点及费用：<https://docs.coze.cn/guides_workflow>
- Coze 知识库分段：<https://docs.coze.cn/guides_knowledge_base_segmentation>
- Coze 新增数据节点：<https://docs.coze.cn/guides_database_insert_node>

我在 2026-10-07 核对了 Coze 页面，并于 2026-10-08 修订提示词、补跑了三题。页面没有显示套餐余额、实际费用或 embedding 单价。表格记录的是目前核实到的状态，2026-10-06 的准备阶段情况不再作为 Coze 当前进度。

Windows 依赖和 embedding 实测见 `WINDOWS_ENVIRONMENT.json`。TASK-017 的 fake 服务/UI smoke 和真实 DeepSeek 状态工具 smoke 分别记录在 `../runs/smoke-20261006-204949/manifest.json`、`../runs/campus-agent-smoke-20261006-205048/manifest.json`。TASK-018 的真实 Streamlit→FastAPI→`deepseek-flash` 合成状态问答见 `../runs/ui-preview-20261006-2105/live-ui-app-test.json`；浏览器预览服务的配置见 `../runs/ui-preview-20261006-210701/manifest.json`。这次 UI 响应没有返回 token usage，所以我没有估算费用；该请求不在 `API_USAGE.jsonl` 的 275 条可量化记录中。Prompt 评分明细见 `评分表_V1_V2.csv`，浏览器截图在提交包中。更早的 Prompt 对照和 RAG 运行记录分别见 `../runs/rag-prompt-ab-v1-20261006-175830/`、`../runs/rag-prompt-ab-v2-20261006-175916/` 和 `../runs/rag-unknown-v2-20261006-180143/`。TASK-017/018 检查过 Docker daemon 和 Compose 配置；本地 SQLite 预览没有启动 Docker。
