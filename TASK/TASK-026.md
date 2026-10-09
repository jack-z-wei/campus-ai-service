# TASK-026：Python 原理版与工程版 Windows 端到端复跑

- 日期：2026-10-08（Asia/Shanghai，按运行记录）
- 状态：已完成
- 范围：两条本地路线、并发检索缺陷修复、浏览器实操截图、完整测试、最新指标和交付副本复核。

## 执行与验收

| 项目 | 实际结果 | 证据 |
|---|---|---|
| Python 原理版冻结集 | 21/21 案例，23 个回答单元，运行错误 0；M01/M02 复用实现、提示词、来源与冻结集指纹均匹配的真实 Windows 多轮 trace | `runs/e2e-20261008-principles-v2/manifest.json`、`runs/principles-multiturn-20261006-195002-4f73e36b/`、`runs/principles-multiturn-20261006-195021-040ca1f2/` |
| 工程版修复后冻结集 | 21/21 案例、23/23 回答单元完成，运行错误 0 | `runs/e2e-20261008-engineering-v3/manifest.json`、`per_case.jsonl` |
| 缺陷闭环 | 首次复跑的并行首次检索暴露 Chroma 持久客户端初始化竞态；工程版改为带锁的单例初始化，新增 8 线程竞争构造回归测试。修复前 `engineering-v2` 的失败 trace 保留；修复后 U02 两个并行搜索均正常执行 | `src/campus/runtime.py`、`src/agents/campus_tools.py`、`tests/campus/test_knowledge_runtime.py`、`runs/e2e-20261008-engineering-v2/`、`runs/engineering-case-20261008-080344-706720eb/` |
| U02 检索结果 | 工具执行异常已修复；两个预期来源仍只检索到其中一个，来源缺口继续计分并披露 | `runs/e2e-20261008-engineering-v3/`、`runs/e2e-20261008-metrics-v3/metric_results.json` |
| 当前项目全量测试 | Windows Python 3.12.7：244 passed、0 failed、4 skipped、18 warnings，28.16 秒。4 个 Docker 标记用例按默认配置跳过 | `runs/windows-test-summary.json` |
| 原理版独立交付副本 | 包内 `uv.lock` 安装 248 项，CPython 3.13.14；`tests/campus` 35 passed | `submission/02_Python_Version/`，复测后移除临时 `.venv` 和测试缓存 |
| 工程版独立交付副本 | 包内 `uv.lock` 安装 248 项，CPython 3.13.14；完整测试 244 passed、4 skipped、18 warnings，83.37 秒 | `submission/03_AI_Coding_Version/`，复测后移除临时 `.venv` 和测试缓存 |
| 本地网页实操 | Windows 浏览器通过鼠标/键盘完成校园政策提问和合成状态查询；保存首页和含真实响应的页面截图 | `submission/06_Demo/screenshots/engineering_ui_home_20261008.png`、`engineering_ui_status_20261008.png`；实际响应 trace 见 `runs/ui-preview-20261008-073436/` |
| 最新离线指标与答案评分 | 对两条最新路线重算 46 个回答单元；46 条答案 Judge 全部完成。评分模型与生成模型同系列 | `runs/e2e-20261008-metrics-v3/metric_results.json`、同目录 judge 输入/响应 |
| 课程主题映射 | 指导书 Day 1–21 按主题关联项目任务和证据；仅为课程阶段索引。实际执行日保留为 2026-10-06 至 2026-10-08 | `reports/21_day_alignment.md` |
| 提交副本完整性 | 六类目录；manifest 为 1,602 个交付内容文件逐项记录 SHA-256（清单文件自身不计入该数）；不含 `.env`、`.venv`、`.git` 或 Python 测试缓存 | `submission/package_manifest.json` |
| 最终报告链接 | 提交版报告 27 个本地文件/图片链接全部解析成功，0 个失效目标 | `submission/05_Final_Report/final_report.md`、`submission/06_Demo/screenshots/README.txt` |

## 指标与实验边界

- 两条路线在可评分检索样本上的 Recall@1/3/5 为 11.5/12（0.9583）；MRR@5 为 1.0000。U02 的目标来源缺一项，因此没有把工具调用正常伪写成检索成功。
- 答案正确性、忠实度和引用指标为该轮模型 Judge 的判断，评分模型与生成模型同系列；Prompt V1/V2 的专项 Rubric 得分单独记录在 `reports/评分表_V1_V2.csv`。
- 最新记录的模型用量可估计约 US$0.199506（按服务峰时费率、输入缓存未命中假设）。这是估算，不是账单；有一条无 usage 的 Judge 响应及两次浏览器 `/stream` 用量未纳入，平台实扣金额未知。
- 截图来自 Windows 实际运行的本地网页，不声称用户亲自完成课程现场演示。页面状态记录使用合成账号和合成业务数据。

## 结论

两条 Python 路线的冻结集已在 Windows 完整复跑；工程版冷启动并发初始化问题已修复并经回归与全量重跑验证。项目代码测试、独立交付副本测试、网页截图、指标和追溯材料均已归档。U02 来源召回缺口、未执行的 Docker 测试、评分方法说明和未知平台账单继续作为已知边界保留。
