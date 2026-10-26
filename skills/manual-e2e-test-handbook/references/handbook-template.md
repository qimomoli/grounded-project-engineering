# 人工全链路测试手册模板

将本模板中的占位内容替换为已验证的项目事实。不要把未执行的命令或推测的结果写成通过。

## 0. 改造范围完整性

- 最终手册路径：`<skill workspace>/projects/<project-key>/handbooks/<功能名>_<版本>_<run-id>_人工测试手册.md`
- 本轮批量授权摘要：`<approval envelope ID or summary>`
- 可复用入口：`<项目索引路径和全局索引路径>`
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
- 范围清单：`<manifest path>`
- 最终手册：`<handbook path; must match the authorized path>`
- 命令台账：`<command-ledger path; must match the authorized path>`
- 手册状态：`Draft/Running / Blocked / Machine-validated/Done`
- 手册修订号：`<handbook_revision>`
- 最近同步 Case：`<last_synced_case>`
- 最近同步时间：`<last_handbook_sync>`

本节必须能让另一轮会话恢复测试，不得只写“继续测试”或“处理失败”。

## 0.2.1 实时维护记录

手册从首个 Case 前开始维护。每个 Case 完成后立即追加一行，不能等全部机测结束后凭记忆重写。

| 修订号 | 同步时间 | Case | 状态 | 实际结果 | 证据 | 下一动作 |
|---|---|---|---|---|---|---|
| `<handbook_revision>` | `<time>` | `<case-id>` | Draft/Running/Blocked/Done | `<observed>` | `<path>` | `<one action>` |

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

| Case ID | 链路 | 前置独立 Case | 命令台账 Step ID | 预期 | 实际 | 状态 | 证据 |
|---|---|---|---|---|---|---|---|
| L-001 | `<app-a -> app-b>` | `I-001`, `I-003` | `CMD-L-001~CMD-L-003` | `<expected>` | `<observed>` | Pass/Fail/Blocked/Skipped | `<evidence>` |

| Case ID | 变更点 | 命令台账 Step ID | 预期 | 实际 | 状态 | 证据 |
|---|---|---|---|---|---|---|
| M-001 | `<change>` | `CMD-M-001` | `<expected>` | `<observed>` | Pass/Fail/Blocked/Skipped | `<log/response/data>` |

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

## 4.1 环境变量与路径初始化

目标操作系统：`Windows`
命令 Shell：`cmd.exe`
仓库目录：`<absolute path>`
Compose 文件：`<absolute path>`

按顺序执行以下初始化命令。每个变量必须有实际值、来源和格式；禁止在后续步骤首次出现未定义占位符。

```cmd
<cd /d ...>
```

```cmd
<set TEST_PREFIX=...>
```

| 变量 | 值/格式 | 来源 | 验证命令 |
|---|---|---|---|
| `<VAR>` | `<value or format>` | `<repo/config/operator>` | `<CMD-STEP-ID>` |

## 4.2 可执行命令总表

本手册必须能脱离聊天上下文执行。下面的表覆盖启动、数据、触发、核验和清理；每行只放一个命令或一个完整 UI 动作。

| 步骤 | 阶段 | 工作目录 | 命令/动作 | 预期输出/状态 | 实际结果 | 通过标准 | 证据 |
|---|---|---|---|---|---|---|---|
| P-001 | 前置检查 | `<cwd>` | `<one exact command>` | `<expected>` | `<observed>` | `<rule>` | `<path>` |

命令必须来自 `command-ledger.md`。最终手册中不得保留 `<short cmd>`、`<short cmd or action>`、`<steps>`、`<docker command>`、`<short cleanup cmd>` 或等价的未定义动作占位符。

## 4.3 操作者执行说明

1. 按 `Win + R`，输入 `cmd`，回车打开命令提示符。
2. 只复制代码块中的命令内容；代码块上的 `cmd` 标签不是命令。
3. 按顺序一次执行一条命令，粘贴后按回车，确认预期输出后再继续。
4. 先执行变量初始化命令；所有 `<PLACEHOLDER>` 必须按变量表替换，不能原样执行。
5. 命令返回非预期结果时停止当前 Case，保存命令、输出和时间，执行对应失败诊断命令。

## 5. 启动与健康检查（逐条可复制）

1. 工作目录：`<cwd>`；执行：

```cmd
<exact startup command>
```

预期退出码/输出：`<expected>`；实际：`<observed>`；证据：`<path>`。

2. 健康检查：

```cmd
<exact health command>
```

预期：`<status/body/log>`；不通过时执行：`<one diagnostic command>`。

3. 每个 fixture、responder 和消息订阅者都必须单独列出启动命令、监听地址、输入格式和停止命令。

## 6. 测试数据准备（逐条可复制）

1. 先执行变量和前置数据命令：

```cmd
<exact setup command>
```

2. 数据库操作必须给出完整 Docker 命令、表、字段和值：

```cmd
<docker exec/compose exec database command>
```

3. Redis 操作必须给出完整 Docker 命令、key、value、TTL 和验证：

```cmd
<docker exec/compose exec redis command>
```

4. 消息、文件或 HTTP 输入必须给出 payload 和发送命令。记录生成的 ID、业务键和数据前缀：`<values>`。

## 7. 新功能人工场景

### A-001 `<scenario name>`

- 目的：`<why>`
- 前置数据：`<data>`
- 操作：
  1. 工作目录：`<cwd>`；执行：

     ```cmd
     <exact command or fully specified UI action>
     ```

     预期：`<exit code/response/log>`；实际：`<observed>`。
  2. 执行：

     ```cmd
     <exact verification command>
     ```

     预期：`<expected>`；失败时：`<diagnostic command and stop/escalate rule>`。
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
  1. 工作目录：`<cwd>`；执行：

     ```cmd
     <exact legacy-flow command or fully specified UI action>
     ```

     预期：`<exit code/response/log>`；实际：`<observed>`。
  2. 执行：

     ```cmd
     <exact legacy verification command>
     ```

     预期：`<expected unchanged behavior>`；失败时：`<diagnostic command and stop/escalate rule>`。
- 预期结果：`<unchanged legacy behavior>`
- 通过标准：`<pass rule>`
- 结果：`Pass / Fail / Blocked`
- 备注与证据：`<evidence>`

## 9. 异常、边界与重复执行

| Case ID | 场景 | 命令台账 Step ID | 预期 | 结果 | 证据 |
|---|---|---|---|---|---|
| E-001 | `<validation/permission/retry/idempotency>` | `CMD-E-001~CMD-E-002` | `<expected>` | `<status>` | `<evidence>` |

## 10. 数据与链路核验

| 核验对象 | 命令台账 Step ID | 预期 | 实际 | 证据 |
|---|---|---|---|---|
| 服务响应 | `CMD-V-001` | `<fields/status>` | `<observed>` | `<path>` |
| 日志/消息 | `CMD-V-002` | `<decisive line>` | `<observed>` | `<path>` |
| 数据库 | `CMD-V-003` | `<row/value>` | `<observed>` | `<path>` |
| Redis | `CMD-V-004` | `<key/value/ttl>` | `<observed>` | `<path>` |
| 下游读回 | `CMD-V-005` | `<result>` | `<observed>` | `<path>` |

## 11. 清理与复位

| 步骤 | 工作目录 | 命令台账 Step ID | cmd 命令 | 预期 | 证据 |
|---|---|---|---|---|---|
| 1 | `<cwd>` | `CMD-C-001` | `<exact docker cleanup command>` | `<deleted rows/keys/objects>` | `<path>` |
| 2 | `<cwd>` | `CMD-C-002` | `<exact stop command>` | `<only run services stopped>` | `<path>` |
| 3 | `<cwd>` | `CMD-C-003` | `<exact cleanup verification command>` | `<no test data remains>` | `<path>` |

## 12. 执行记录

| 人员 | 时间 | 环境 | 结果 | 失败/阻塞说明 | 证据位置 |
|---|---|---|---|---|---|
| `<tester>` | `<time>` | `<environment>` | Pass/Fail/Blocked | `<details>` | `<path or link>` |

## 13. 经验沉淀

| 经验 ID | 内容 | 适用模块/条件 | 证据 | 最后验证 | 失效条件 | 归属 |
|---|---|---|---|---|---|---|
| K-001 | `<reusable practice>` | `<scope>` | `<case or failure ID>` | `<version/time>` | `<when to revalidate>` | Project/Cross-project |

写入经验库前删除凭据、Token、个人信息、生产数据、客户数据和不必要的完整日志。业务专用经验只保留在项目记录中。


