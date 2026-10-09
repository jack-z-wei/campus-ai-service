# 失败案例与处理结果

下面记录我在实现和评测中遇到的问题，以及目前的处理结果。每项都对应实际运行或测试记录；单个案例修复后通过，不代表整套系统都没有同类问题。

| 观察到的问题 | 证据 | 影响 | 修正 | 当前状态 |
|---|---|---|---|---|
| **K10：图书馆联系方式查询中旧资料排在当前主页之前** | `runs/retrieval-frozen10-20261006-180107/per_case.jsonl` 的 K10：raw NumPy 的 Recall@1=0、MRR@5=0.333；两个旧页面排第 1/2，`library_home_2026` 排第 3 | 若直接采用 raw Top-1，不能优先提供官方当前主页来源 | 使用来源时效策略过滤 `archive_not_for_current_answers` | 同一冻结查询经 NumPy 和 Chroma 过滤后均将当前主页排第 1；历史 raw 失败保留 |
| 首次真实 API 烟测脚本无法导入项目模块 | 首次 Windows 运行输出 `ModuleNotFoundError: No module named 'core'`；记录在 `runs/api-smoke-launch-failure-20261006/manifest.json` | API 请求未发送 | 脚本先将项目 `src` 加入模块路径；同一请求随后成功 | 修复后成功，0 次失败请求 |
| DeepSeek API 冒烟请求指定 `max_tokens=32`，但返回 75 个 output token，其中 68 个 reasoning token | `runs/api-smoke-20261006-173028/manifest.json` | 该参数不能据当前响应声称有效限制服务端总输出量；费用估算必须以服务端 usage 为准 | 保留响应 usage；调用记录明确标为 requested 值，并记录 observed output 超限。后续 Agent 工具调用前还要验证 thinking 参数与 SDK 协议 | 待 Agent 实验验证 |
| 冻结数据第一次单元测试中，临时文档夹具 chunk metadata 缺少 `source_id` | 首轮 `tests/campus` 输出 1 failed，7 passed | 契约测试不符合真实来源需要的溯源字段 | chunker 无论输入 metadata 如何都显式写入 `source_id` | 修正后 Windows `tests/campus` 10 passed |
| U02 询问中国籍本科生校外住宿流程时，冻结 gold 期待 2 个来源，RAG Top-5 只命中 1 个 | `runs/rag-unknown-v2-20261006-180143/traces/U02.json`：两次检索结果均只有 `international_off_campus_housing_2017`，来源 Recall@5=0.5；answer trace 留存 | 回答正确地拒绝将国际学生 2017 流程外推，但没有检索到另一份可用于流程/联系方式核对的历史学生管理来源；资料覆盖不足可能限制转介信息 | 保留该真实失败作为待改项；后续检查 query rewrite、不同 scope/历史来源检索与过滤策略，但不得把历史规则表述为当前政策 | 答案边界暂时安全；检索召回未修复，不能记为 U02 完整通过 |
| **K01：固定长度切块截断了审批句，模型补出了输入中没有的文字** | 两份初始 trace（`runs/principles-20261006-182118-c183be16/trace.json`、`runs/principles-20261006-182229-bdf65396/trace.json`）显示，Top-1 的 500 字符上下文停在“所在学院审”；完整原句见 `runs/campus-index-20261006-173801/chunks.jsonl` 的 `chunk_index=2`。只加强提示词后，模型仍补完了“审核” | 当轮上下文没有包含回答中的完整审批细节，无法仅凭模型输入核验；提示词约束没有解决切块截断 | 我检查首个高分块的结尾；如果同一来源还有连续片段，就按 `chunk_index` 和源偏移补入下一块，去掉重复的 80 字符，并沿用原文档的来源 ID、URL、日期和效力范围 | 修复 trace `runs/principles-20261006-182445-b9893872/trace.json` 显示，补块后的模型上下文能够拼接出“所在学院审核并报教务处批准”这一完整表述。K01 单例已修复，不能据此推断全量语料均无切块问题 |
| 原理版冻结 S01 只给记录编号，工具却强制模型额外提供服务类别；模型追问类别，未调用状态工具 | 首次真实运行 `runs/principles-20261006-182527-52cdfe74/trace.json`：1 次模型回复、0 次 Tool Call | 冻结案例预期查出模拟状态；让模型从记录号猜服务类别不合适，追问使这一题未完成 | 状态工具改为必填当前模拟身份与记录号，服务类别可选；省略时 SQLite 在 `record_id + owner_user_id` 范围内解析本人的唯一行，仍可显式类别精确过滤。冻结集原 gold 未更改 | 同一 S01 重测 `runs/principles-20261006-182725-6b464d98/trace.json`：1 次 `query_application_status`，返回合成状态。工具参数少于冻结 gold 中预期的 `service_type`，需在精确参数指标中单列，不按原参数金标准记全对 |

## TASK-008 双路线多轮复测

我让原理版和工程版按顺序分别运行了冻结用例 M01、M02，并给两组测试使用独立的 SIM 身份和 session。M01 都先追问再查到状态；M02 都在第二轮调用了模拟转人工工具，并在本地保存工单。逐轮 trace 均已保留，工程版测试随后删除了 checkpoint thread。本轮没有发现新的工具选择、多轮记忆或工单持久化问题，因此没有新增失败案例；已有的 K01、S01、U02 和早期探索问题仍按原记录保留。

## TASK-010 固定集审计与新增多轮挑战

我把冻结基线逐轮结果保存在 `runs/frozen-eval-v1-20261006/metric_results.json`，可以据此重新计算指标。阶段 E 的失败案例和计数口径见 `evaluation/failure_cases.json` 与 `TASK/TASK-011.md`。

| 新增观察 | 实际证据 | 判断 |
|---|---|---|
| U02 来源召回不足 | `runs/rag-unknown-v2-20261006-180143/traces/U02.json` 与 Principles / Engineering 基线及优化单例均只含 `international_off_campus_housing_2017`，冻结 gold 有两个来源，Recall@5=0.5 | 多次运行仍是同一个查询与根因；仅计 1 个不同场景。Engineering 的建议部门超出检索片段支持范围 |
| K01 固定长度块中断审批句 | 两份初始 trace 的 Top-1 文本均以“所在学院审”结束；第二次只加强 Prompt 后问题仍存在 | 独立于 U02 的知识查询与切块边界问题；答案对截断后的内容作了补全，证据上下文不足 |
| K10 旧版图书馆资料压过当前主页 | raw NumPy 冻结10结果中，两个 archive 页面排名 1/2，正确主页排名 3；Recall@1=0、MRR@5=0.333 | 独立于 K01/U02 的来源排序与时效过滤问题；过滤策略后本题在 NumPy、Chroma 均恢复为主页第 1 |
| S04 无身份仍调用状态工具 | Principles `runs/principles-20261006-191646-895b16dd/trace.json`、Engineering `runs/engineering-case-20261006-192046-f1d6ba53/traces/turn_01.json` | 都返回 `invalid_identity`，未泄漏状态数据；但模型工具定义中仍有状态工具，属不必要且可避免的工具选择 |
| B01 跨身份拒绝未调用 gold 指定工具 | 同基线两条路线 B01 trace | 答复拒绝跨用户查看，语义安全；与 gold 的“调用工具后得到 forbidden”冲突，因此 Tool Selection / Task Completion 记失败，冻结 gold 不擅自修改 |
| 同一 thread 更换模拟身份时旧状态仍在模型上下文 | `evaluation/challenge_cases_v1.json`；修复前 Windows SQLite-checkpointer 集成挑战首次运行失败，第二轮模型输入仍有 SIM-USER-001 的工具结果“材料审核中” | 真实实现边界缺陷；挑战采用 deterministic fake model 检查图/存储上下文，不据此声称 LLM 输出失败。修复后同一回归测试通过 |
| UI 可选参数传递回归 | Windows 全量测试首轮 `237 passed, 1 failed, 4 skipped`，失败为 `tests/app/test_streamlit_app.py::test_app_settings`；`src/streamlit_app.py` 将 `agent_config=None` 传入客户端 | 按固定上游调用约定仅在配置非空时传入；随后全量测试 `238 passed, 4 skipped` |
| 批次 trace 索引路径缺失 | 初次聚合因父级 per-case manifest 引用未能解析而失败；Windows 批次索引按稳定 child `run_id` 修复路径，聚合器增加该 ID 回退 | 不重跑 API 修好父级索引并完成 46 份 Judge 输入聚合；多轮复用逻辑增加代码/Prompt/数据指纹以避免跨版本重用旧 trace |

### U02 来源范围复核

我检查了现有的 `student_management_2017.md`，它只要求学生遵守另行制定的宿舍规定，没有说明国内本科生校外住宿的申请流程；另一份国际学生文件则明确只适用于来华留学生。学校公开的[来华留学生校外住宿管理办法](https://webplus.chd.edu.cn/_s21/2017/1026/c2596a37145/page.psp)和[2025 国际学生入学问答](https://webplus.chd.edu.cn/en/2025/0227/c8889a248803/page.psp)也不能用来补国内学生的流程。因为我没有找到可安全加入语料的现行规则，U02 的 Recall@5 仍为 0.5；我没有用不适用的联系人来填补答案。

我把 K01、K10 和 U02 分别作为三个失败问题分析：K01 是切块截断，K10 是归档来源排在当前来源之前，U02 是第二个来源未召回。K01 和 K10 已按各自原因修复，修复前的 trace 也保留了下来；U02 仍未解决。三项对应不同查询和原因，不是同一问题的重复运行。
