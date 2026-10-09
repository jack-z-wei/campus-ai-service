# TASK-004：冻结来源审查与验收用例

- 日期：2026-10-06（Asia/Shanghai）
- 状态：已完成（数据集与工具契约冻结；运行结果待对应实现）
- 目标：在实施业务代码和观察模型输出前固定评测题、来源清单版本及状态查询工具验收约定。
- 范围：不把评测预期当成实际运行结果，不用模型输出反向生成 Gold，不含真实学生数据。

## 验收条件

1. 固定评测集共 21 题：知识 10、状态 5、多轮 2、未知 2、边界 2。
2. 每题的知识 Gold 可追溯至本地来源清单，状态数据明确为合成数据。
3. 评测集绑定当前官方校园来源清单 SHA-256；来源变化时要求重新审查。
4. 状态工具契约包含 3 个正常、2 个错误和 1 个不存在用例；契约仅定义预期，不记录未运行的结果。

## 已完成

- 冻结 `evaluation/frozen_cases.json`，21 题类别数量满足项目约定；知识 Gold 均引用 `source_manifest.json` 中的来源 ID。
- Gold 基于来源快照及显式 `SIM-` 种子数据编写，未由系统回答生成。
- 将来源清单 SHA-256 `05e297bcf2fc85151e7741c9a1fa33a995d3e3b122a49630f6318c7c499c0b4c` 写入冻结评测元数据。
- 建立 `evaluation/status_tool_contract.json`，定义 3 个所有权匹配的正常查询、无身份/非法编号错误及未找到记录。
- Windows 完整性校验：21 题、分类计数一致、14 个来源可解析、4 条种子均是合成标识；冻结来源哈希一致。

## 文件与证据

- `evaluation/frozen_cases.json`
- `evaluation/status_tool_contract.json`
- `scripts/check_frozen_evaluation.py`
- 来源版本：`docs/campus/source_manifest.json`

## 未解决事项

- 这些用例目前是冻结规范，不代表业务工具、RAG 或 Agent 已通过。
- 下个任务为 TASK-005：仅从来源清单导入校园文件，构建 Loader、三类 Chunker 和本地 embedding 数据；随后实现状态工具并运行本契约。
