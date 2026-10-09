# TASK-027：Coze H-02 交付核对、提示词修订与补充复测

- 日期：2026-10-08（Asia/Shanghai）
- 状态：已完成（Coze 平台修改、补充复测、Windows 提交包与哈希复核均完成）
- 范围：对照《两天实施计划》H-02 核查 Coze 真实平台证据；修复过时状态；针对知识来源时效提示进行受控修改和同题复测，不改写原冻结输出。

## H-02 核对结果

| 要求 | 实际记录 | 证据 |
|---|---|---|
| 建立并运行真实 Bot；至少 5 个早期校园问答 | K01/K05/K06/K09/K10 已有 Coze 实答和截图 | `coze/screenshots/03_Agent与K01.png`、`09`–`13`；`coze/results.csv` |
| 知识引用、未知处理、状态、模拟转接、多轮 | 原始 14 题 / 16 助手轮次覆盖分类；两个 Workflow 有发布版本与合成执行 | `coze/results.csv`、`coze/screenshots/`、`coze/logs/agent-evaluation-20261007.md` |
| 两组真实切分和同题输出 | A：500 字符/双换行/16% 重叠/2,084 片；B：700 字符/单换行/0%/2,365 片；K01 在 A/B 实跑 | `coze/experiment_sheet.csv`、截图 09、22 |
| 至少 10 个固定用例 | 原始冻结执行 14 题 / 16 轮；7 条空白仍为未执行 | `coze/results.csv`、`coze/evaluation_minimum_cases.json` |
| 同题三路线对照 | K01 和 S02 各三路线实际输出，共 6 行 | `reports/three_track_comparison.csv` |
| 配置、日志和截图 | 原配置/运行证据、工作流设计与 2026-10-08 提示词及补测证据均归档 | `coze/截图清单.md`、`coze/workflow/`、`coze/logs/`、`coze/retests/20261008/` |

H-02 技术材料和运行数量齐备，不代表教师签收、Agent 公开发布或每条答案都通过。

## 2026-10-08 平台操作与结果

- 从已登录 Edge 打开 Coze 中的 Agent 草稿“长安大学校园智能客服”。实际模型界面显示豆包·2.0·pro；没有改账号配置、套餐、工作流、知识库或发布状态。
- 将知识问答提示词补强为明确披露来源日期/年份、区分正文/目录/HTTP 修改时间、限定适用对象、说明历史材料当前效力，以及证据不足时不编造联系方式。Coze 编辑器显示草稿自动保存时间 10:42:12；从页面复制提示词后与项目版规范化比较为 1,161/1,161 字符完全一致。前后文本分别见 `coze/logs/platform-prompt-snapshot-20261008.txt` 和 `coze/logs/platform-prompt-updated-20261008.txt`。
- 按原题面再次运行 K01、K06、K09，逐条输出/判定见 `coze/retests/20261008/retests.csv`：
  - K01：数字与审批正确；Agent 指出检索片段没有日期，但没有可确认的日期/链接，保留 partial。
  - K06：40 工时/月与 2016 正文年份正确；仍未解释目录 2025-08-03 与 PDF 正文 2016-07-12 日期冲突及现行效力未核实，保留 partial。
  - K09：补充输出包含 2017-10-26、原来源链接、仅限来华国际学生与当前效力未确认，复测通过。
- 原始 `coze/results.csv` 完全保留；原冻结结果中 5 条 partial 与 7 条未在 Coze 执行的用例没有因补测重算或覆盖。
- 平台显示 Agent 仍为草稿。没有公开发布。页面未显示本次请求的实际费用/账户余额，因此账单状态保持未知。

## 文件更新

- 修正 Coze 模块映射、H-02 验收清单、测试集状态、用户说明、外部依赖和最终报告中的陈旧“尚未执行”描述。
- 更新项目内 `coze/instructions.txt`，并保存平台前后提示词副本；新增补充复测 CSV、实际输出记录及 3 张平台截图。
- 更新 Coze 执行 manifest 和打包器，使根提交包摘要区分原始冻结结果与补充复测结果。
- Windows 打包器已执行；六目录提交包与哈希清单已生成。

## 限制

- 冻结运行仍是 14 题 / 16 助手轮次；另 3 条同题补测单列。7 个冻结题没有在 Coze 运行，不补写结果。
- 仍存在 K01/K06 partial；S02/B01 原始截图未展开 Agent 的完整工具 trace，平台完整 source ID、部分节点参数、稳定 run ID、账单和 embedding 单价不可观测。
- 转接 Workflow 的 request_key 去重、关联记录归属二次校验和异常补偿没有验证；状态身份是合成值而非认证。
- Agent 为未公开草稿。此任务不声称教师签收、部署上线或费用已核验。

## 交付验收结果

- Windows 重新生成六目录提交包，Coze 文件、报告链接与最新截图/复测材料齐全。
- Manifest 中文件数、SHA-256 与目录实际状态一致；报告相对链接无失效目标；无 `.env`、`.venv` 和密钥。
- 以上验收标准均满足；项目记录保留剩余偏差和未核验事项。

## Windows 交付复核

- 项目 Windows 虚拟环境运行 `scripts/build_submission_package_windows.py`，生成 6 个规定目录及 1,614 个带 SHA-256 的交付文件；manifest 标记无 `.env`，没有打包 `.venv` 或 `.git`。
- Windows 虚拟环境运行 `scripts/check_coze_package_windows.py`，结果通过：原始固定集14题/16轮、5条原始 partial、7条未在 Coze 运行、补测3条（K09 pass、K01/K06 partial）、平台提示词往返逐字核对通过；34张 Coze 截图已复制，1,614个提交文件哈希匹配。
- `reports/final_report.md` 与提交副本各核对34个本地文件/图片链接，失效目标0个。
- 未声称教师签收、Coze Agent 公开发布或账单核验；平台草稿保持未发布。
