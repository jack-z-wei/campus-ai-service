# 工程版上游来源与改动记录

我在工程版中复用了公开项目 JoshuaC215/agent-service-toolkit 的部分基础代码。来源信息如下：

- 仓库：https://github.com/JoshuaC215/agent-service-toolkit
- 分支：main
- 固定提交：88ebfa1fadd1a207aa92115635abf7ed20d66a88
- 许可：MIT，原始 LICENSE 保留
- 获取日期：2026-10-06（Asia/Shanghai）

## 我复用了哪些内容

上游提供 LangGraph 模型与工具调用流程、FastAPI 服务、Streamlit 对话界面、schema 和服务辅助模块、SQLite checkpoint 记忆及依赖锁。我以这套工程结构搭建工程版，但上游代码本身不能证明校园业务功能已经实现或验证；本项目的校园用例仍以自己的代码和运行记录为准。

## 我为课程项目补充的内容

校园知识来源和 Loader 元数据、三种切分策略、BGE-M3 接入、向量检索实验与来源引用检查、校园工具 schema 和 SQLite 合成数据、Python 原理版、冻结用例、评测、Coze 材料、报告和演示材料，均是我为本项目编写或整理的内容，没有作为上游已有功能申报。

## 会话记忆与删除接口

我检查了锁定依赖中的 `src/service/service.py`：FastAPI 启动时会为 LangGraph Agent 配置 SQLite saver。校园 Agent 使用同一 saver，并通过运行时配置接收 `thread_id`、`user_id`、`agent_id` 和合成身份。

上游 `AsyncSqliteSaver` 提供 `adelete_thread(thread_id)`，可以删除对应 thread 的 checkpoint 和 write 记录。我在调用前核对已保存的 `user_id`、`agent_id`，并为服务端点、`AgentClient` 和 Streamlit 增加删除支持。真实 SQLite 测试检查了本人 thread 可以删除、跨用户请求返回 404。

校园 Agent 使用项目自己的 `StateGraph`。模型输入最多包含最近四轮从 HumanMessage 开始的对话；完整 checkpoint 会保留到用户主动删除为止。这段上下文窗口是本项目的实现，不是上游模板自带功能。Python 原理版没有运行 LangGraph Agent，因此用独立 SQLite 表保存已完成的文本问答，每个 session 最多保留四轮，并绑定合成用户身份。

上游服务接收调用方提供的 `user_id`，并没有提供真实的校园身份认证。删除接口中的用户和 Agent 检查只能避免误删其他 thread，不能替代认证。界面和报告都按这一边界说明。

## 课程要求中的复用问题

课程选型材料要求从空目录开始，但没有明确说明是否允许用完整的第三方工程骨架。我还没有拿到教师答复，因此在此披露固定提交、许可和复用范围，不声称已经获得教师许可。

## 复现时处理的问题

完整测试曾遇到 `test_app_settings` 失败。我检查后发现，上游 `src/streamlit_app.py` 在没有额外 agent 配置时，会不传 `agent_config` 参数调用 `AgentClient.ainvoke`。校园界面保留了这个可选参数的调用方式：没有配置演示身份时不发送该字段。

上游还提供 LangSmith 的单次运行评分入口（`src/client/client.py`、`src/service/service.py`、`src/streamlit_app.py`），但它不会计算本项目的 Retrieval、Answer、Agent、Engineering 四层指标，也不保存本地 trace 与 manifest 的关联；这条路径还需要外部 LangSmith 配置。因此我仍使用项目内冻结集和 Rubric 评测。

我也检查了上游 RAG 示例和固定 Top-K retriever。它们没有本项目所需的校园来源范围规则，也没有适用于 U02 的国内本科生现行住宿材料，无法解决这次观察到的来源缺口。U02 仍按实际运行结果保留为未解决问题。
