# 人工全链路测试手册模板

将本模板中的占位内容替换为已验证的项目事实。不要把未执行的命令或推测的结果写成通过。

## 0. 改造范围完整性

- 范围状态：`Complete / Incomplete`
- 基线分支/提交：`<baseline branch or commit>`
- 测试分支/提交/构建：`<test branch, commit, or build>`
- 改造来源：`<conversation, requirement, bug, PR, commit IDs>`
- 已检查来源：`<diff/history/docs/API/schema/events/tests>`
- 改造点总数：`<count>`
- 已确认改造点：`<count>`
- 受影响旧功能数：`<count>`
- 未知影响数：`<count>`
- 明确排除范围：`<excluded areas>`
- 清单版本/校验时间：`<manifest revision and time>`

只有范围状态为 `Complete`，并且未知影响已解决或明确接受为未覆盖风险，才允许将本手册标记为机测通过后的最终版本。

## 0.1 测试运行状态

- 运行标识：`<run-id>`
- 最终阶段：`<phase>`
- 最终状态：`Running / Blocked / Done / Recovery incomplete`
- 最后检查点：`<YYYY-MM-DD HH:mm:ss>`
- 中断/恢复次数：`<count>`
- 当前或最后 Case：`<case-id>`
- 下一动作：`<single actionable step>`
- 状态文件：`<run-state path>`
- 事件日志：`<event-journal path>`

本节必须能让另一轮会话恢复测试，不得只写“继续测试”或“处理失败”。

## 0.2 自助排查与人员求助

| Request ID | Case/Failure | 阻塞现象 | 已尝试 | 关键证据 | 请求人员提供/执行 | 响应 | 恢复结果 |
|---|---|---|---|---|---|---|---|
| O-001 | `I-003 / F-001` | `<blocker>` | `<max three distinct attempts>` | `<evidence>` | `<specific input/action>` | `<response or no response>` | `Resumed/Blocked/Rejected` |

规则：同一症状最多三次有不同假设的低风险排查；不得无新证据重复同一失败命令。超过预算、需要新增权限/范围或需要人员判断时，必须暂停并求助。等待期间不猜测、不继续轮询，直到收到并验证人员输入。

## 1. 测试概览

- 项目标识：`<stable project key>`
- 项目来源：`<sanitized remote identity or local path fingerprint>`
- 运行标识：`<YYYYMMDD-HHMMSS-commit>`
- 功能/改造：`<feature or change>`
- 代码版本或构建号：`<commit/build>`
- 机器测试时间：`<YYYY-MM-DD HH:mm:ss>`
- 本地环境：`<compose file, service versions, OS>`
- 测试范围：`<new behavior and affected legacy behavior>`
- 机测阶段：`应用独立容器验证 -> 多应用链路联调`
- 独立验证门禁：`Pass / Fail / Blocked`
- 限制与未覆盖项：`<evidence-backed gaps>`

## 1.1 历史参考与有效性

| 历史资料 | 关联原因 | 最后验证版本/时间 | 当前复核结果 | 使用方式 |
|---|---|---|---|---|
| `<handbook or experience ID>` | `<module/API/schema/topic match>` | `<version/time>` | Valid/Stale/Rejected | `<reused setup/case/diagnosis>` |

历史 `Pass` 不能继承。本次使用的命令、预期和回归范围必须按当前版本重新核验和执行。

## 2. 机器测试结果

机测分为两个阶段：先完成所有受影响应用的独立容器验证，再执行多应用链路联调。

### 2.0 应用独立容器验证

| 应用/服务 | 独立容器 | 最小依赖 | 健康/配置/连接检查 | 容器级改造功能 Case | 直接结果/数据证据 | Maven/单测辅助结果 | 结果 | 证据 |
|---|---|---|---|---|---|---|
| `<app-a>` | `<container>` | `<db/cache or none>` | `<checks>` | `I-001`, `I-002` | `<response/log/db/Redis>` | `<optional auxiliary result>` | Pass/Fail/Blocked | `<evidence>` |

容器级改造功能 Case 必须通过正在运行的应用容器验证本次变更行为。Maven/单测只能作为辅助结果，不能单独将应用独立验证判为 `Pass`。只有所有必需应用的容器级独立验证为 `Pass`，才允许执行多应用链路联调。

### 2.0.1 多应用链路联调

| Case ID | 链路 | 前置独立 Case | 命令/动作 | 预期 | 实际 | 状态 | 证据 |
|---|---|---|---|---|---|---|---|
| L-001 | `<app-a -> app-b>` | `I-001`, `I-003` | `<short cmd or action>` | `<expected>` | `<observed>` | Pass/Fail/Blocked/Skipped | `<evidence>` |

| Case ID | 变更点 | 命令/动作 | 预期 | 实际 | 状态 | 证据 |
|---|---|---|---|---|---|---|
| M-001 | `<change>` | `<short cmd or action>` | `<expected>` | `<observed>` | Pass/Fail/Blocked/Skipped | `<log/response/data>` |

状态含义：

- `Pass`：按通过标准执行并观察到证据。
- `Fail`：执行完成但结果不符合预期。
- `Blocked`：因环境或前置条件无法完成。
- `Skipped`：未执行；不得计入通过。
- `Not applicable`：有明确证据说明不适用。

## 2.1 失败诊断与修复记录

每个失败或不符合预期的 Case 都必须保留记录。没有成功重测证据时，不得改写为 `Pass`。

| Failure ID | Case ID | 现象与证据 | 分层排查 | 根因/候选原因 | 建议方案 | 人员确认 | Remediation ID | 重测结果 |
|---|---|---|---|---|---|---|---|---|
| F-001 | `M-001` | `<response/log/data>` | `<API/service/db/Redis/message/env>` | `<confirmed or hypotheses>` | `<options and risk>` | `<person/time/scope>` | `X-001` | `<retest Case and result>` |

修复流程：先记录失败证据和建议，等待人员确认；确认后记录批准的文件、服务、数据和命令范围；修复后重测失败 Case，并回归所有直接受影响的旧功能和跨服务链路。修复被拒绝、范围不清或重测失败时，状态保持 `Fail` 或 `Blocked`。

## 3. 变更追踪

| 变更点 | 新功能机器 Case | 旧功能回归 Case | 人工场景 |
|---|---|---|---|
| `<change>` | `M-001` | `M-004` | `A-001`, `R-001` |

覆盖规则：每个已确认改造点至少关联一个机器 Case 和一个人工场景；未覆盖改造点必须写明原因，不能留空或默认视为不影响。

## 4. 前置条件与安全边界

1. 确认使用 `<local compose file>`，仅操作本地容器。
2. 确认所需环境变量、账号和测试凭据：`<list>`。
3. 所有测试数据使用前缀：`<prefix>`。
4. 不连接生产、共享或远程环境。

## 5. 启动与健康检查

1. `<short cmd>`
2. `<short cmd>`
3. 预期：`<container health and service readiness>`。

## 6. 测试数据准备

1. `<short cmd>`
2. 数据库操作必须使用容器命令：`docker compose exec <db> <client> ...`。
3. Redis 操作必须使用容器命令：`docker compose exec <redis> redis-cli ...`。
4. 记录生成的 ID、业务键和数据前缀：`<values>`。

## 7. 新功能人工场景

### A-001 `<scenario name>`

- 目的：`<why>`
- 前置数据：`<data>`
- 操作：
  1. `<UI/API action>`
  2. `<short cmd or observation>`
- 预期结果：`<expected>`
- 观察点：`<response/log/message/database/Redis>`
- 通过标准：`<pass rule>`
- 结果：`Pass / Fail / Blocked`
- 备注与证据：`<evidence>`

## 8. 受影响旧功能回归

### R-001 `<legacy scenario>`

- 受影响关系：`<change point and reason>`
- 前置数据：`<data>`
- 操作：
  1. `<step>`
  2. `<short cmd or observation>`
- 预期结果：`<unchanged legacy behavior>`
- 通过标准：`<pass rule>`
- 结果：`Pass / Fail / Blocked`
- 备注与证据：`<evidence>`

## 9. 异常、边界与重复执行

| Case ID | 场景 | 操作 | 预期 | 结果 | 证据 |
|---|---|---|---|---|---|
| E-001 | `<validation/permission/retry/idempotency>` | `<steps>` | `<expected>` | `<status>` | `<evidence>` |

## 10. 数据与链路核验

- 服务响应：`<verified fields/status>`
- 日志或消息：`<container and decisive line>`
- 数据库：`<docker command and expected row/value>`
- Redis：`<docker command and expected key/value/ttl>`
- 下游读回：`<verified result>`

## 11. 清理与复位

1. `<short cleanup cmd>`
2. 使用与准备阶段相同的前缀删除测试数据。
3. `<short stop cmd>`（仅停止本次启动的服务，除非另有约定）。
4. 复查：`<container/data cleanup evidence>`。

## 12. 执行记录

| 人员 | 时间 | 环境 | 结果 | 失败/阻塞说明 | 证据位置 |
|---|---|---|---|---|---|
| `<tester>` | `<time>` | `<environment>` | Pass/Fail/Blocked | `<details>` | `<path or link>` |

## 13. 经验沉淀

| 经验 ID | 内容 | 适用模块/条件 | 证据 | 最后验证 | 失效条件 | 归属 |
|---|---|---|---|---|---|---|
| K-001 | `<reusable practice>` | `<scope>` | `<case or failure ID>` | `<version/time>` | `<when to revalidate>` | Project/Cross-project |

写入经验库前删除凭据、Token、个人信息、生产数据、客户数据和不必要的完整日志。业务专用经验只保留在项目记录中。


