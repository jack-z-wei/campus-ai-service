# 最终工程核对（早期提交快照）

核对日期：2026-10-08（Asia/Shanghai）。这份文件保留较早提交副本的核对结果；后续的最终结果请看 `05_Final_Report/FINAL_AUDIT.md`。TASK 中的旧测试数字也仍按记录当时的结果保留。

## 核对结果

| 核验项 | 当前结果 | 证据 |
|---|---|---|
| Python 原理版冻结集 | 21/21 案例、23 个回答单元完成，0 个执行错误 | `runs/e2e-20261008-principles-v2/` |
| AI 工程版冻结集 | 修复后 21/21 案例、23 个回答单元完成，0 个执行错误 | `runs/e2e-20261008-engineering-v3/` |
| Chroma 并发冷启动缺陷 | 已修为带锁单例初始化，新增竞争初始化回归测试；完整重跑通过 | `src/campus/runtime.py`、`tests/campus/test_knowledge_runtime.py`、TASK-026 |
| 当前 Windows 项目测试 | Python 3.12.7；244 passed、0 failed、4 skipped、18 warnings，28.16 秒 | `runs/windows-test-summary.json` |
| 两条独立交付副本 | 分别按包内 `uv.lock` 安装 248 项，CPython 3.13.14；原理版 35 项 campus 测试通过，工程版完整测试见 `reports/package-verification.json` | `submission/02_Python_Version/`、`submission/03_AI_Coding_Version/` |
| 浏览器验证 | Windows 本地前端实际输入校园政策问题和合成状态问题；首页与含返回答案的页面真实截图已归档 | `submission/06_Demo/screenshots/`、`runs/ui-preview-20261008-073436/` |
| 指标和 Judge | 两路线共 46 个回答单元，最新模型辅助 Judge 已完成；评价模型和生成模型同系列 | `runs/e2e-20261008-metrics-v3/` |
| 课程主题映射 | 指导书 Day 1–21 已逐项映射任务和材料；真实任务日期为 2026-10-06 至 2026-10-08 | `reports/21_day_alignment.md` |
| 提交目录 | 6 个规定目录；manifest 为 1,614 个交付内容文件逐项记录 SHA-256（清单文件自身不计入）；未含 `.env`、`.venv`、`.git` 和常见 API key 格式 | `submission/package_manifest.json` |
| 提交报告链接 | 34 个本地文件和图片链接均已解析，失效目标 0 个 | `submission/05_Final_Report/final_report.md` |
| Coze 范围 | H-02 原始技术交付含14题/16轮、两组切分、工作流和三轨对照；平台提示词已修订并逐字核对。原始集5条 partial；另有3条同题复测，K09通过，K01/K06仍partial。34张 Coze 截图与逐题限制已归档。Agent 未公开发布、Coze 费用未知；不表示教师签收 | `coze/验收补齐清单.md`、`coze/package_manifest.json`、`coze/retests/20261008/`、`submission/01_Coze_Version/` |

## 结果说明

- 两条路线在 12 个有 gold source 的回答单元上 Recall@1/3/5 均为 11.5/12（0.9583），MRR@5 为 1.0。工程 U02 的并发工具调用异常已修复，但第二个预期来源仍未召回；当前 retrieval 指标保留该缺口。
- 答案正确性、忠实度和引用分数由同系列模型按固定 Judge prompt 生成；10 份 V1/V2 答案另按统一 Rubric 评分，详见 `评分表_V1_V2.csv`。
- 可取得的模型 token usage 按峰时公开单价、输入缓存未命中估算约 US$0.199506；这不是账单。一次 Judge 请求和两次浏览器 `/stream` 的 token usage 不可见，Coze 实际费用亦未核实。
- Day 1–21 是实验指导书的课程主题编号，不代表自然日进度。本轮项目记录日期如上所列，没有伪造 21 天工作日记。
- 4 个 Docker 标记测试按默认 pytest 设置跳过。未声称教师许可、平台发布、用户现场演示或课程平台正式提交已完成。

## 交付索引

- 最终报告：`reports/final_report.md`
- Day 1–21 主题和真实材料映射：`reports/21_day_alignment.md`
- 任务进度：`reports/PROGRESS.md`
- 最终双路线运行记录：`TASK/TASK-026.md`
- 打包文件及 SHA-256：`submission/package_manifest.json`
- Windows 页面截图：`submission/06_Demo/screenshots/`
