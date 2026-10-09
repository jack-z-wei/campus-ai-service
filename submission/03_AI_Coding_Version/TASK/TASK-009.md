# TASK-009：Coze 配置包与人工实测交接

- 日期：2026-10-06（Asia/Shanghai）
- 状态：配置包已完成并通过本地内容检查；Coze 账号核验与平台实测待用户。
- 目标：为独立 Coze 版本准备可直接上传的知识材料、模拟业务数据、工作流合同和固定测试记录表；不把本地模拟或官方文档误报为平台实测。
- 验收：14 份知识快照能回对来源，4 行合成状态种子，21 行空白结果，2 组空白分段实验，状态/工单节点合同，用户操作说明、截图清单及显式未实测 manifest。

## 已准备文件

- `coze/knowledge/`：14 份官方校园来源快照。
- `coze/source_manifest.csv`、`coze/knowledge_files.sha256`：元数据和文件 hash。
- `coze/instructions.txt`：知识范围、模拟身份、状态和工单行为约束。
- `coze/workflow/`：合成状态种子、空工单表、`schema.md`、`node_contract_matrix.csv` 与 `build_steps.md`。
- `coze/test_cases.md`、`coze/result_template.csv`：冻结的 21 例和空白真实结果记录。
- `coze/experiment_sheet.csv`：两组待在 Coze 实际界面中核对并配置的分段实验，设置、切片数、答案和证据列均未伪填。
- `coze/用户操作说明.md`、`coze/README.md`、`coze/截图清单.md`：账号/费用能力核验和实测材料。
- `coze/package_manifest.json`：`prepared_not_platform_tested`，`platform_account_checked=false`，`paid_coze_request_performed=false`。

## 检查和修正

- 首次 Windows 内容检查只验证资料、seed、空白结果表和两组实验。
- 随后发现生成器的字符串分隔符未闭合，导致 `instructions.txt` 混入后续生成器源码，并跳过部分静态文件落盘。没有覆盖知识快照或实验结果；没有执行任何 Coze 平台调用。
- 修复 `scripts/prepare_coze_package_windows.py` 的字符串边界，并重建系统说明、schema、节点矩阵、搭建说明、README 和截图清单；增加用户操作指南。
- 扩展 `scripts/check_coze_package_windows.py` 检查静态文件存在、生成器源码未泄漏、3 个校园节点合同、10 个未勾选证据项以及 manifest 声明。
- Windows 项目 Python 执行 `py_compile` 成功；包完整性检查通过：14 份资料、4 行模拟状态、21 行空白结果、2 组未执行配置、3 条节点合同、6 项交接文件；Coze 实测次数 0，收费 Coze 请求 0。
- 一次早期检查因 Windows CRLF/LF 解码前按原始字节相比较而误报快照不一致；改为 UTF-8 文本内容对照，哈希仍保留为字节级快照标识。该检查改动不改变被测文件内容。

## 人工待办与边界

- H-02 见 `reports/HUMAN_TODO.md`：在用户真实 Coze 工作空间核验页面、模型/Embedding 费用提示、分段设置字段/单位和数据库节点能力；核验前不运行有收费可能的模型或插件节点。
- Coze 官方公开文档仅作为配置参考，不能证明实际账号权限、版本、费用和节点输出。
- 状态与工单完全使用合成数据；SIM 身份不是认证；工单不会联系真实工作人员。
- 平台尚未登录、未建 Bot/知识库/表、未运行题目、未生成截图或平台 trace。manifest 必须保持未实测状态，直至逐项获得真实平台证据。
