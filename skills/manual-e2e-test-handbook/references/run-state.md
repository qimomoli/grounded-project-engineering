# 长时间测试运行状态

本规则让测试在会话压缩、进程中断或长时间等待后可以从持久化状态恢复。它记录流程控制，不替代当前代码、Compose 或实际容器状态。

## 运行目录

```text
workspace/projects/<project-key>/runs/<run-id>/
|-- run-state.json
|-- event-journal.jsonl
|-- machine-results.md
`-- evidence/
```

这些路径必须在本轮批量授权中列出。`run-state.json` 可原子替换；`event-journal.jsonl` 追加写入；两者都不得包含凭据、Token 或完整敏感日志。

## 状态格式

```json
{
  "run_id": "20261023-143000-a1b2c3d",
  "project_key": "project-a-1a2b3c4d5e",
  "manifest_path": "projects/project-a-1a2b3c4d5e/manifests/功能_版本_20261023-143000-a1b2c3d_改造范围清单.md",
  "handbook_path": "projects/project-a-1a2b3c4d5e/handbooks/功能_版本_20261023-143000-a1b2c3d_人工测试手册.md",
  "authorized_output_paths": [
    "projects/project-a-1a2b3c4d5e/manifests/功能_版本_20261023-143000-a1b2c3d_改造范围清单.md",
    "projects/project-a-1a2b3c4d5e/handbooks/功能_版本_20261023-143000-a1b2c3d_人工测试手册.md",
    "projects/project-a-1a2b3c4d5e/runs/20261023-143000-a1b2c3d/run-state.json",
    "projects/project-a-1a2b3c4d5e/runs/20261023-143000-a1b2c3d/event-journal.jsonl",
    "projects/project-a-1a2b3c4d5e/runs/20261023-143000-a1b2c3d/machine-results.md",
    "projects/project-a-1a2b3c4d5e/runs/20261023-143000-a1b2c3d/evidence/*.log"
  ],
  "phase": "APPLICATION_ISOLATION",
  "status": "running",
  "current_case": "I-003",
  "completed_cases": ["I-001", "I-002"],
  "failed_cases": [],
  "blocked_cases": [],
  "attempt_count": 1,
  "last_attempt": "检查 app-b 容器健康状态和最近日志",
  "operator_request": null,
  "next_action": "读取 app-b 容器日志并确认 Redis 连接状态",
  "approval_envelope": "本轮批量确认摘要或 ID",
  "last_checkpoint": "2026-10-23T14:35:12+08:00",
  "last_evidence": ["evidence/I-003-response.txt"]
}
```

## 允许的阶段

```text
SCOPE_CHECK
APPLICATION_ISOLATION
LINK_INTEGRATION
FAILURE_TRIAGE
WAITING_FOR_OPERATOR_INPUT
WAITING_FOR_FIX_APPROVAL
RETEST
REGRESSION
PERSIST_RESULTS
DONE
```

阶段只能按 skill 规定的顺序前进。应用独立验证未全部通过时不能进入 `LINK_INTEGRATION`；需要人员输入时只能停在 `WAITING_FOR_OPERATOR_INPUT`；失败修复未获批准时只能停在 `WAITING_FOR_FIX_APPROVAL`；未完成重测和回归时不能进入 `PERSIST_RESULTS`。

## 自助排查与求助字段

每个症状和 Case 最多进行三次有不同假设的低风险排查。`attempt_count` 必须在每次尝试后递增，不能通过重写状态清零。相同命令、相同输入和相同环境下不得重复执行并声称是新尝试。

进入 `WAITING_FOR_OPERATOR_INPUT` 时，`operator_request` 至少包含：

```json
{
  "request_id": "O-001",
  "case_id": "I-003",
  "failure_id": "F-001",
  "blocker": "缺少本地设备标识",
  "attempts": ["检查环境变量", "读取容器日志"],
  "evidence": ["evidence/I-003-log.txt"],
  "needed": "请提供一个本地测试设备 ID，格式为 TEST-<数字>",
  "after_response": "使用该 ID 重试 I-003",
  "waiting_since": "2026-10-24T10:00:00+08:00"
}
```

等待期间不得继续猜测、轮询或重复重试。收到输入后先写 `operator_response` 事件，验证输入，再更新唯一的 `next_action`。

## 检查点规则

每个 Case 后以及每个容器、数据或服务状态变化前后更新检查点。检查点必须说明：

- 当前阶段和 Case；
- 已完成、失败和阻塞的 Case；
- 预期与实际结果；
- 证据位置；
- 批量授权是否仍覆盖下一动作；
- 唯一且可执行的 `next_action`。

一个 `next_action` 只描述一个动作。不要写“继续测试”或“处理失败”这类不可恢复的模糊描述。

## 事件格式

`event-journal.jsonl` 每行一个 JSON 事件，例如：

```json
{"time":"2026-10-23T14:35:12+08:00","event":"case_started","case_id":"I-003"}
{"time":"2026-10-23T14:36:01+08:00","event":"case_failed","case_id":"I-003","failure_id":"F-001"}
{"time":"2026-10-23T14:37:20+08:00","event":"checkpoint","phase":"FAILURE_TRIAGE","next_action":"保存日志摘要"}
```

事件追加后再更新状态文件。状态文件表示当前控制点，事件日志表示发生过的事实；两者冲突时暂停并报告，不凭记忆选择一个。

## 恢复顺序

1. 读取状态文件和最近事件。
2. 读取改造范围清单、最近机器结果和批准范围。
3. 核对当前 Git 提交、项目规则、Compose 文件和容器状态。
4. 将中断时仍为 `running` 的 Case 标为 `Blocked` 或重新执行，不能默认通过。
5. 确认阶段、当前 Case 和唯一下一动作后，先写恢复检查点。
6. 只执行该 `next_action`，完成后再写新的检查点。

如果无法恢复阶段、当前 Case、批准范围、重试次数、操作人员请求或下一动作，状态设为 `Recovery incomplete`，停止测试并报告缺失信息。若恢复后发现同一症状已达到三次尝试，直接进入 `WAITING_FOR_OPERATOR_INPUT`，不得重新开始无限排查。


