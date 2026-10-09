# Coze 测试数据库表的字段合同与边界

我在 Coze 个人空间中用状态表和模拟工单表保存课程演示数据。状态表按单用户模式配置，业务记录标记为 simulation_only=true。下表只列出页面中能核实的字段；SIM ID 是合成测试值，不是登录身份或校园认证。

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

状态查询工作流实际以 AND 组合 record_id、service_type 和 owner_sim_user_id，最多返回一条记录。owner 匹配、跨 owner 和无记录三种情况都有截图；Agent 预览没有导出每个案例的完整 workflow 参数。

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

模拟工单工作流有平台试跑和 Agent M02 写入记录。平台返回的工单编号按截图中可见内容记录。request_key 重放去重、关联记录 owner 二次核验、异常补偿和并发幂等没有在本次实验中验证，因此这里只把它们列为字段合同，不写成已实现结果。
