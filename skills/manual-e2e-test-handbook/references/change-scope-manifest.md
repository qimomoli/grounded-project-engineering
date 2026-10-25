# 改造范围清单

本清单用于抵抗长会话、上下文压缩和多轮需求追加造成的范围遗漏。它是测试范围的事实来源之一，不替代代码差异、需求文档或用户确认。

## 使用规则

- 每次开始或恢复测试时先读取并刷新清单。
- 记录基线、测试版本、来源、检查范围和清单修订号。
- 只有有具体证据支持的改造点才能标记为 `Confirmed`。
- `Inferred`、`Unknown`、`Incomplete` 不能进入最终机测通过门槛。
- 用户追加改造后递增修订号，并重新检查旧功能影响和测试矩阵。
- 机测结果必须引用清单中的稳定 Case ID，不用聊天中的临时编号替代。

## 清单头部

```text
Manifest revision: <M-REV>
Scope status: Complete / Incomplete
Project key: <stable project key>
Project identity evidence: <sanitized remote or local path fingerprint>
Run ID: <YYYYMMDD-HHMMSS-commit>
Baseline: <branch or commit>
Test version: <branch, commit, or build>
Sources: <conversation, requirement, bug, PR, commit IDs>
Inspected repositories/modules: <list>
Inspected source range: <commit/time range>
Last verified: <YYYY-MM-DD HH:mm:ss>
Unknown impacts: <count and IDs>
Excluded areas: <explicit exclusions>
Historical references: <handbook and experience IDs>
Isolation gate: <Pass / Fail / Blocked>
Affected applications: <application/service list>
Run state: <phase / status / current Case / next action>
Last checkpoint: <YYYY-MM-DD HH:mm:ss>
Operator requests: <request IDs and status>
```

## 改造点表

| Change ID | 状态 | 改造描述 | 证据来源 | 涉及模块/服务 | 受影响旧功能 | Isolation Cases | Link Cases | Manual Cases | Failure/Remediation | 未知/限制 |
|---|---|---|---|---|---|---|---|---|---|
| C-001 | Confirmed/Inferred/Unknown | `<behavior change>` | `<file, commit, doc, or conversation ref>` | `<module/service>` | `<legacy flow>` | `I-001` | `L-001` | `A-001`, `R-001` | `F-001 / X-001` | `<risk or none>` |

## 完整性检查

```text
[ ] 基线和测试版本已固定
[ ] 所有改造来源已列出
[ ] 当前 diff 和相关提交已检查
[ ] 需求/缺陷/设计来源已检查（若存在）
[ ] API、数据库、消息、缓存影响已检查
[ ] 每个 Confirmed 改造点都有 Machine Case
[ ] 每个受影响应用都有 Isolation Case
[ ] 每个 Isolation Case 都启动对应应用容器并验证本次改造行为
[ ] Maven/单测仅作为辅助证据，未单独满足 Isolation gate
[ ] 所有 Isolation Case 通过后才执行 Link Case
[ ] 每个 Confirmed 改造点都有 Manual Case
[ ] run-state 和 event-journal 已创建并在每个 Case 后更新
[ ] 当前 Case、下一动作和恢复状态可从持久化记录还原
[ ] 同一症状的自助排查不超过三次且每次有不同假设
[ ] 需要人员输入时已进入 WAITING_FOR_OPERATOR_INPUT
[ ] 操作人员请求、响应和恢复结果已记录
[ ] 受影响旧功能已逐项识别
[ ] Unknown 影响已解决或明确记录为风险
[ ] 排除范围已明确
[ ] 用户已确认范围完整（需要时）
[ ] 历史资料已按当前版本复核，未继承旧 Pass
```

只有全部适用项完成后，才将 `Scope status` 改为 `Complete`。

## 失败与修复记录

| Failure ID | Case ID | 现象/证据 | 根因状态 | Remediation ID | 批准范围 | 修复版本 | 重测 Case | 回归结果 |
|---|---|---|---|---|---|---|---|---|
| F-001 | M-001 | `<evidence>` | Confirmed/Hypothesis/Unknown | X-001 | `<approved files/services/data>` | `<commit/build>` | `M-001R` | `<legacy cases and results>` |

修复记录必须能回答：谁确认了什么范围、改了什么、在哪个版本重测、哪些旧功能重新回归、是否仍有风险。


