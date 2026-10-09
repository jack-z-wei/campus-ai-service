# TASK-024：Coze 平台实现、测试与报告证据

- 日期：2026-10-07（Asia/Shanghai）
- 授权：用户要求完成 Coze 所有必需项目；已授权浏览器操作、真实平台测试与相关模型调用。不得把人工评价、报告个人签署或公开发布假称为已完成。
- 状态：Coze 配置、两条工作流、14题/16轮平台用例、A/B 与检索参数对照、三轨同题运行及报告证据已完成；保留平台能力和责任人限制。
- 续接：复用既有个人空间 A/B 知识库、application_status、human_service_ticket、Agent 草稿；没有重复初始化。

## Coze 实际配置

1. A/B 知识库各包含14份资料，Coze 页面显示2,084和2,365个分片；结束时只将知识库 A 挂载到 Agent。
2. Agent：长安大学校园智能客服，单 Agent 自主规划模式，页面显示豆包·2.0·pro；深度思考关闭。自动知识库调用、混合搜索、Top-K=5、最低匹配度0.50、查询改写和结果重排开启。A 库是唯一挂载库。
3. 两个工作流连接至 Agent：
   - campus_service_status_query，ID 7693891212118818854：记录号、服务类型、合成 owner 同时匹配，最多一行；真实工作流测试覆盖 owner 匹配、跨 owner 和无记录。
   - campus_human_service_demo，ID 7693901471003689023：明确请求后写入合成工单；真实平台试跑生成 ID 7693904260018454543。Agent 的 M02 又创建一条，ID 7693919908337303579。记录标记 simulation_only=true，不通知真人。
4. Agent 草稿自动保存；未点击公开发布。两条工作流在个人空间发布了版本，供个人 Agent 调用。

## 已执行 Coze 课程用例

- 14个用例、16个 assistant turn：知识 K01/K05/K06/K09/K10；状态 S01/S02/S05；多轮 M01/M02；未知 U01/U02；边界 B01/B02。
- A/B 同题、Top-K/最低匹配度对照均实际运行；恢复最终配置为 Top-K=5、最低匹配度0.50。
- K01 与 S02 在 Coze、Python 原理版、LangGraph 工程版均有实际输出，三轨表6行已填写。
- 逐题结果：coze/results.csv。A/B 记录：coze/experiment_sheet.csv。检索参数：coze/retrieval_parameter_comparison.csv。运行总结：coze/logs/agent-evaluation-20261007.md。
- 新截图 09–25 和已存在的工作流截图均保存在 coze/screenshots/；截图索引为 coze/截图清单.md。

## 观察到的偏差与限制

- K01 原始冻结题面回答核心答案正确并引用办法标题，但未显示具体日期或提醒现行有效性未知；加“标出来源”的同题运行会显示日期和链接。
- K06 虽然指出 PDF 正文落款2016年，但没有披露文件目录标注2025年及现行性未核验；K09 指出了国际学生范围和2017日期，但未提示当前办理流程需复核。
- S02 Agent 结果正确，但截图未展开 workflow trace。Coze SIM 编号由用户在提示中提供，不是认证。
- B01 回复拒绝跨身份查询，但截图未展开 workflow trace，不能独立核验没有发出工具调用。
- M02 实际工具调用可见；工单工作流没有测试 request_key 去重、关联记录 owner 校验或失败补偿。只能作封闭合成数据演示。
- 平台无法导出所有 source ID、完整 workflow arguments、稳定 run ID、embedding 单价或账号实际账单。Coze UI 的响应计时与本地耗时口径不同。
- Agent 未公开发布。真人评分、个人信息/心得/签署和教师许可仍按 reports/HUMAN_TODO.md 处理。

## 关键证据

- 状态 workflow：coze/screenshots/workflow-status-owner-match.png、workflow-status-cross-user-empty.png、workflow-status-published.png。
- 两个 workflow 与 Agent：coze/screenshots/05_Agent工作流接入.png、06_campus_human_service_demo流程.png、07_campus_human_service_demo发布记录.png。
- 真实 Agent 测试：coze/screenshots/08_Agent状态查询-修正后.png、14–21。
- A/B 与参数比较：coze/screenshots/09_Agent-K01-学分检索.png、22–24。
- 同题三轨 Coze 输出：coze/screenshots/25_Agent-K01-三轨同题基线.png；六行对照 reports/three_track_comparison.csv。

## 验收判定

- Coze 页面配置与分类用例执行：完成。
- 两工作流存在已发布个人空间版本并有合成数据执行：完成，限制如上。
- A/B、检索参数、三轨对照：完成，属于单次实测观察，不夸大因果或整体排名。
- Coze Agent 公开发布：未执行；保持草稿。
- 平台账单、真人评分、个人签署、教师许可：未完成且不能由平台测试代替。
