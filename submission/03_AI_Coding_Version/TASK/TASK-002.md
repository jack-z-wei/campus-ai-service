# TASK-002：需求矩阵、费用和平台路线

- 日期：2026-10-06（Asia/Shanghai）
- 状态：已完成（文档与人工依赖交接）；真实账号执行待后续任务
- 目标：把课程要求、上游许可、API 费用和 Coze 可行性形成可核验矩阵，明确人工交接和不阻塞工作。
- 范围：课程 Markdown、官方 DeepSeek / Coze 文档、选定上游提交；不访问用户账号，不推断余额或权限，不调用付费 API。

## 验收条件

1. `requirements_matrix.md` 覆盖知识、Chunk、Embedding、检索/RAG、Tool、Agent、Memory、评测、Coze、三轨、报告与提交。
2. `EXTERNAL_DEPENDENCIES.md` 标明 Windows 组件、Key、预算、价格依据、Coze 限制及未确定状态。
3. `UPSTREAM.md` 固定 repo/commit/license、复用/自主范围与待教师确认事项。
4. `HUMAN_TODO.md` 只列当前需要用户做的事，给出位置、完成标志和影响。
5. 未获 Key 和平台账号确认前不发生收费调用；报告不得把计划或文档能力写成实测结果。

## 已执行

- 用户最初授权 ¥50 上限，随后明确取消金额上限；当前按实验范围分批调用并记录 usage。
- DeepSeek 官方文档当前列出 `deepseek-flash`、OpenAI 兼容地址和 Tool Calls；Coze 官方文档列出工作流数据库查询/新增节点和知识库自定义分段。
- 已创建课程要求矩阵、依赖记录、上游固定版本说明和教师确认文案。
- 费用静态估算仅保留为量级参考；用户当前未设总金额上限。单次输出与请求范围仍受控，真实请求后记录服务端 usage 和当日价格。
- DeepSeek Key 已配置在本地 `.env`；Coze 费用与账号状态仍未知，不将 DeepSeek 授权推断为 Coze 状态。
- Windows 环境及模板服务烟测已完成，详见 TASK-001；fake 响应不计入课程效果。

## 证据

- `reports/requirements_matrix.md`
- `reports/EXTERNAL_DEPENDENCIES.md`
- `UPSTREAM.md`
- `reports/HUMAN_TODO.md`

## 未解决事项

- DeepSeek 实际联通尚未执行，计划接入用量记录后验证。
- Coze 账号、模型、平台余额、功能权限、界面与收费状态未知。
- 教师是否接受第三方模板底座待确认。
