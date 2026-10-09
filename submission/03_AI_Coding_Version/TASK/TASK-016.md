# TASK-016：Windows 独立复现、提交包与最终自动审计

- 日期：2026-10-06（Asia/Shanghai）
- 自动部分状态：已验收
- 课程最终交付状态：待人工/平台验收
- 依据：《两天实施计划.md》阶段 G、报告模板和课程验收清单。

## 已完成

- `submission/` 已整理为六类目录：Coze 交接材料、Python 原理版、LangGraph 工程版、完整评测证据、报告、演示脚本。平台截图和人工评分仍留为空白状态；README 明确说明未完成验收项。
- 运行 Windows Python 项目环境的 `uv sync --frozen`，分别在两个独立交付目录新建临时虚拟环境并按随包 `uv.lock` 安装 248 个锁定依赖。uv 选择 CPython 3.13.14，处于 `requires-python >=3.12,<3.15` 和锁文件支持范围内；项目主环境为 Python 3.12.7。
- 独立 Python 版 `tests/campus -q`：35 passed，0 failed，0 skipped，5.45 秒。
- 独立工程版全量 `pytest -q`：242 passed，0 failed，4 skipped，18 warnings，55.84 秒。4 个 Docker 标记测试按默认策略跳过。
- `02_Python_Version` 以包自身虚拟环境进行 K01 本地 Ollama embedding/NumPy retrieval-only 烟测，`status=retrieval_only_complete`；未调用聊天 API，未产生付费模型请求。运行 ID 为 `principles-20261006-202257-4f3fc9c1`。
- 两个包的 Settings 配置检查都指向各自包根目录的 `.env`，两个包中都不存在 `.env`。检查时只在独立 Windows 进程中设置未记录的校验占位值，不写入任何文件或调用服务。
- 首轮独立 Python 包测试发现 allowlist 漏拷 `evaluation/human_service_contract.json`（34 passed / 1 failed）；已纳入打包源规则并复制到包内，复跑 35/35 通过。失败原因和修复保留在本记录与 `reports/package-verification.json`。
- 测试生成的包内 `__pycache__` 等缓存与临时 `.venv` 在最终校验前清理；打包扫描规则现排除 `.venv`、VCS、Python 和 pytest/ruff/mypy 缓存、`.env`，并检查 API key 常见 `sk-...` 模式但不输出匹配内容。
- 首轮报告链接审计发现三轨 CSV 链接替换规则未匹配带反引号的 Markdown 标签，导致打包报告 1 个相对链接无目标；已修复生成器替换规则和当前副本，Windows 再查 9 个本地链接全部存在。
- 最终提交清单由 Windows 项目 `.venv` 运行 `scripts/build_submission_package_windows.py --refresh-manifest` 生成；`submission/package_manifest.json` 为六目录中所有交付文件计算 SHA-256，清单排除自身。最终文件数及校验状态见 `reports/FINAL_AUDIT.md` 和 manifest。
- 截至本阶段（2026-10-06），API 用量文件没有新增付费调用，Coze 调用为 0；2026-10-07 的 K01 预览记录见下方后续更新。

## 曾遇到并保留的问题记录

- 独立 Python 首轮测试因合同 JSON 未打包失败；修复后通过。
- 第一次包清单刷新被测试产生的 `__pycache__` 阻止；已扩展排除扫描并只清除自动生成的运行环境/缓存，再重验。失败日志只在对话工具输出中，没有被当成通过结果。
- `uv` 在新目录选择 3.13.14。检查 `pyproject.toml` 和 `uv.lock` 确认该版本属于支持范围；版本差异在 `reports/package-verification.json` 保留。

## 尚未完成的课程人工项

- H-01：轮换曾在对话中暴露的 API Key，并更新本机 `.env`。本交付包无 `.env`。
- H-02：真实 Coze 工作空间配置、费用/权限确认和 K01/S02 两条平台实测。
- H-03：V1/V2 十行回答人工评分及理由。
- H-04：个人身份、真实分工、个人反思与签署。
- H-05：Windows 浏览器现场核验与教师提交格式/渠道确认。
- H-07：向老师核实固定 upstream 骨架复用许可。

上述操作位置、完成标准和回填文件见 `reports/HUMAN_TODO.md`、`reports/报告待填写项.md`、`coze/用户操作说明.md`。未将空表、合成状态或本地结果伪装为平台/人工证据。

## 2026-10-07 后续更新

- 用户提供并确认从 Windows Coze 页面截图目录筛选报告用图；5 张原始图现已归档到 `coze/screenshots/`，提交版 Coze 目录与报告已同步。
- 单次 K01 预览按真实画面登记为部分通过；H-02 全量平台验收仍待完成。因此，旧清单中的 `coze_platform_tested=false` 继续表示“完整平台验收未完成”，不代表没有任何预览记录；manifest 另列 `coze_partial_preview_recorded=true`。
- 本次只做材料同步、相对链接核验和提交 manifest 重算，没有重跑项目功能测试或 Coze 用例集。

## 2026-10-07 TASK-024 后续更新

- Coze 平台运行、工作流及 14 题/16 助手轮次、A/B/检索参数对照和三轨材料现已由 TASK-024 完成；本节上方“全量平台验收仍待完成”仅描述早先截图阶段。
- 最新 Coze 证据已同步到 `submission/01_Coze_Version/coze/`；Windows Python 再次重算六类提交目录 manifest，共 1,222 个文件，报告 20 个本地链接均解析到现存目标。

## 验收范围

自动复现与交付包结构验收通过；这不代表 Coze、人工评分、报告签署、教师许可或最终提交已完成。必须完成人工项后，才能把课程整体交付标记为完成。
