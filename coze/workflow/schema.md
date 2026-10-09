# Coze 测试数据库表的字段合同与边界

Coze 个人空间中使用状态表和模拟工单表承载课程演示数据，状态表采用单用户模式。业务记录标记 `simulation_only=true`。平台系统字段以实际界面为准，不推断隐藏字段；SIM ID 是合成测试值，不是登录身份或校园认证。

## application_status

| 字段 | 类型 | 说明 |
|---|---|---|
| record_id | string | `SIM-REC-###` |
| owner_sim_user_id | string | `SIM-USER-###` 合成身份 |
| service_type | string | aid_application / scholarship_application / dorm_repair / library_service |
| status | string | 合成状态 |
| updated_at | string | ISO 8601 +08:00 |
| public_note | string | 合成备注 |
| simulation_only | boolean/string | 固定 true |

状态工作流实测条件以 AND 组合 `record_id`、`service_type`、`owner_sim_user_id`，查询上限 1；owner 匹配、跨 owner 和无记录直接试跑均有截图。Agent 预览未为每个案例导出完整 workflow arguments。

## human_service_ticket

| 字段 | 类型 | 说明 |
|---|---|---|
| requester_sim_user_id | string | 合成请求者 |
| service_type | string | dorm_repair_followup / aid_application_followup / library_service_followup / general_student_service |
| record_id | string，允许空 | 只能关联当前合成用户的记录 |
| reason | string | 1–500 字 |
| status | string | 初始 `created_simulated` |
| request_key | string | 同一会话/调用去重键 |
| simulation_only | boolean/string | 固定 true |

模拟工单工作流有真实平台试跑与 Agent M02 写入证据，实际返回的平台记录编号只按可见结果记录。`request_key` 重放去重、关联记录 owner 二次核验、异常补偿和并发幂等未经过本次验证；不得把合同中的预期当成已实现事实。
