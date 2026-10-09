# TASK-021：校园客服界面重塑、真实截图与 V1/V2 评分

- 状态：校园界面改造、真实截图与 10 份 V1/V2 Rubric 评分已完成
- 日期：2026-10-06
- 目标：将对外界面与工程交付说明聚焦为长安大学校园智能客服；基于已保存回答和 trace 完成统一 Rubric 评分。

## 已实施

- Streamlit 页面改为中文校园服务布局，只连接 `campus-customer-service`；移除工具箱标题、上游架构/作者/源码链接、LangSmith 隐私说明、通用 Agent 选择与内部工具参数/输出展示。
- 校园页面说明知识问答、合成业务状态和模拟人工服务的边界；演示身份明确为合成数据。
- 根 README 与工程交付 README 改为校园客服项目说明；包构建器启用专用工程 README 生成，保留 `UPSTREAM.md` 与原始 MIT `LICENSE`，如实记录工程来源。
- 新增 `reports/评分表_V1_V2.csv`，逐条核对 10 份存档答复与来源 trace；每题分三项记录评分与理由，评分者记为 Codex。

## 验收标准

- Windows AppTest / 校园定向测试通过，页面无上游产品品牌与通用 Agent 面板。
- Windows 浏览器能打开实际校园客服页面；截图来自真实运行页面，不做合成或内容编辑。
- 交付包 README、界面与截图使用校园服务表达；许可证与来源披露文件保留。
- 评分覆盖 10 行并附每项理由；V1、V2 各 30/30。
- `submission/package_manifest.json` 与最终文件 SHA-256 一致，未携带 `.env`。

## 结果

- Windows `tests\app\test_streamlit_app.py tests\campus`：59 passed；`tests\core\test_settings.py`：26 passed；Ruff 与 py_compile 通过。应用/校园测试触发 4 条上游依赖弃用警告。
- Windows `/health`、`/_stcore/health`：HTTP 200。Chrome 中实际打开页面，截图 `reports/campus_ui_home.png` 为 1721x845，未对应用内容做合成或编辑。
- V1 和 V2 各 5 行 Rubric 评分均 30/30；评分依据与 trace 路径均已保存。
- 本任务无模型/API 调用。MIT LICENSE 与 `UPSTREAM.md` 保留；记录撰写时 Coze 平台项仍待处理，后续结果见 TASK-024；个人资料/签署、真人 H-03 与现场 H-05 仍待人工。交付 manifest 已更新。
