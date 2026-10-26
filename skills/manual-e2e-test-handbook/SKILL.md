---
name: manual-e2e-test-handbook
description: Use when a conversation-driven feature change or bug fix needs local Docker-backed validation and a reproducible Chinese manual end-to-end test guide, including regression coverage for affected legacy behavior.
metadata:
  short-description: 先机测再生成可执行人工全链路测试手册
---

# Manual E2E Test Handbook

Use this skill when the user wants a local, step-by-step manual test guide derived from feature changes, bug fixes, or behavior changes discussed in the conversation. The skill validates the relevant behavior in a local environment first, then writes the handbook from the commands and observations that actually worked.

## Operating contract

- Treat the conversation as the primary change request, then verify it against repository evidence: current diff, requirements, API/protocol definitions, Docker Compose files, startup docs, tests, database schema, cache keys, and event/message definitions.
- Separate confirmed facts from inference. Do not invent ports, credentials, container names, table names, Redis keys, payload fields, or expected values. Use placeholders and mark blockers when repository evidence is missing.
- Scope all execution to the local project environment. Never target production, shared environments, or remote hosts.
- Before any service start, restart, test-data write, database/Redis mutation, or cleanup, show the user the exact bounded targets, compose file, service list, data scope, and cleanup plan. Wait for explicit confirmation. Read-only inspection may happen before confirmation.
- Never claim a case passed when it was skipped, partially observed, or inferred from source code.
- Do not infer that the visible conversation contains the complete change scope. Create or refresh a durable change-scope manifest before designing cases, and reload it whenever the conversation is resumed or compressed.
- Store generated manifests, handbooks, sanitized evidence, and learned practices under this skill's own `workspace/` tree, never in the tested project's repository unless the user explicitly requests another location.
- Treat the current run as a recoverable state machine. Persist the phase, current Case, completed Cases, blockers, next action, approval envelope, and last checkpoint; do not rely on conversation memory for control flow.
- When machine testing becomes difficult, make a bounded self-resolution attempt and escalate to the operator instead of looping. Record every attempt and stop when the retry budget or evidence boundary is reached.
- Record Windows `cmd.exe` as the command environment in the run state and handbook. This skill's manual commands are Windows `cmd.exe` only; do not emit PowerShell, Bash, WSL, or POSIX variants.
- Treat the final handbook as an executable runbook, not a narrative test report: every setup, trigger, verification, failure branch, and cleanup action must have an exact command or a fully specified UI action, defined inputs, expected output, pass rule, and evidence location.

## Workflow

### 1. Establish change and environment scope

Build or refresh a durable change-scope manifest using [references/change-scope-manifest.md](references/change-scope-manifest.md). Keep one row per behavior:

`change point -> new behavior -> affected old behavior -> service/component -> observable evidence -> candidate cases`

Record the scope boundary before testing:

- baseline branch or commit;
- test branch, commit, or build;
- requirement, bug, PR, or conversation source IDs;
- repositories, modules, services, and time/commit range inspected;
- confirmed change points, affected legacy flows, unknown impacts, and excluded areas;
- manifest revision and last verification time.

Inspect the smallest useful set of repository files. Prefer project-local instructions and existing test or smoke scripts over newly invented setup. Identify:

- the local compose file or documented startup entry point;
- services, health checks, exposed ports, dependencies, and required environment files;
- existing automated tests, API examples, fixture scripts, migration/seed instructions, and log locations;
- data stores and the exact schema/key/topic evidence needed for verification;
- cleanup and reset mechanisms that are safe for a local environment.

Use multiple evidence sources where available: conversation, current diff, commit history, requirements/bug/design documents, API/protocol definitions, schema/migrations, event/message definitions, and existing tests. A change is `Confirmed` only when at least one concrete source supports it; otherwise mark it `Inferred` or `Unknown`.

Run a scope-completeness gate before creating executable cases. Report the number of discovered change points, the sources inspected, the number of affected legacy flows, unresolved unknowns, and excluded areas. If the baseline/test boundary is missing, source coverage is incomplete, or any unknown could change the required regression set, stop and ask the user to confirm or complete the scope. Do not start containers or produce a final handbook while the manifest is `Incomplete`.

If the environment cannot be bounded to local resources, or required setup information is missing, stop and report the blocker before starting services.

When returning to a long or resumed conversation, reload the manifest and compare its revision, baseline, current commit, and source list with the repository. Reconcile new evidence before relying on prior case IDs or test results.

Before designing cases, read [references/historical-reuse.md](references/historical-reuse.md). Resolve a stable project key, inspect the global catalog, then load only history relevant to the current project, modules, APIs, tables, Redis keys, or message topics. Historical material is supporting evidence, never proof that current behavior passes.

### 2. Design the machine-test matrix

Create executable cases from every `Confirmed` change point before running them. Include, as applicable:

- happy paths for every new capability;
- validation, malformed input, empty/not-found, permission, timeout, retry, idempotency, and duplicate-event behavior;
- cross-service request, message, storage, cache, and read-back paths;
- every old flow whose API, schema, status, event, cache, or shared component changed;
- compatibility checks for unchanged callers and old data;
- cleanup and repeatability checks when the change is stateful.

Split the machine matrix into two explicit phases:

- `I-*` application-isolation cases: one case set per affected application or service. Each case must start that application's container, verify health/configuration and minimal dependencies, then exercise the changed behavior through the running container (exposed API, protocol, message, scheduled trigger, or other observable application entry point) and verify its direct result and relevant storage/cache effects.
- `L-*` multi-application link cases: end-to-end flows crossing two or more applications, including request, message/event, storage, cache, downstream, and read-back behavior.

Every application involved in a confirmed change must have an isolation result before any link case can run. A service may be grouped with a minimal required dependency only when the dependency is explicitly recorded; grouping all applications into one stack is not an isolation check.

For each case record: ID, relation to a change point, preconditions, data setup, exact command or UI action, expected result, observation point, pass rule, and evidence to retain.

Maintain separate coverage for new behavior, affected legacy behavior, unknown impact, and explicitly excluded behavior. Every confirmed change point must map to at least one machine case and one manual case, unless a written `Not applicable` reason is recorded.

Maven or other host-side unit tests may be recorded as auxiliary evidence, but they never satisfy an `I-*` isolation gate by themselves. A passing unit-test suite without a running application container and a changed-behavior functional check is insufficient. Existing container smoke, API, protocol, or contract checks may be reused only when they exercise the affected behavior through the running application; otherwise add a focused container-level case.

### 3. Confirm and run local machine tests

Before mutating anything, present a short execution approval containing:

- the stable `project-key` and this run's `run-id`;
- compose file or startup script;
- services to start or restart;
- local endpoints to call;
- database/Redis containers and data operations;
- test-data scope and unique prefixes;
- cleanup commands and whether they are destructive;
- the case IDs that will be run;
- the exact final handbook path for this `run-id`, plus every planned manifest, sanitized evidence, project metadata, experience, and index file, using exact paths or narrowly bounded run-specific patterns;
- the run-state file, event journal, machine-result file, and evidence pattern for this `run-id`;
- the command ledger file `runs/<run-id>/command-ledger.md`;
- the statement that this single approval covers creation and updates of those listed files for this run, including the final handbook and its index entries.

This is the run's batch authorization envelope. It is valid only for the listed `project-key`, `run-id`, operations, resources, and paths, and ends when the run completes or is abandoned. After approval, create and update the listed handbook, experience, manifest, evidence, metadata, and index files without asking again for each write.

Ask again only when a later action introduces an unlisted path or resource, broadens the data or service scope, deletes/moves/renames an artifact, performs an unapproved destructive operation, or attempts remediation outside the approved envelope. A test failure does not expand the envelope.

After confirmation:

1. Resolve the affected application list and the minimal dependency set for each application.
2. Run application-isolation verification one application at a time: start only its container and recorded minimal dependencies, verify health/configuration/connectivity, then execute the changed-behavior functional case through the running container and capture direct result plus storage/cache evidence. Run Maven/unit tests only as supplementary checks.
3. Do not start multi-application link testing until every required application has passed its isolation gate. Record failed or blocked applications and stop at this gate.
4. Prepare isolated, uniquely prefixed test data for the approved link scope.
5. Start the approved multi-application set and run new-feature link cases, affected legacy link regressions, then repeatability checks.
6. Verify externally visible responses and internal evidence such as logs, database rows, Redis values, messages, and downstream read-back.
7. Capture concise command output and the exact observed values needed to support each result.
8. Clean up the created data and stop only services started for this run, unless the user asked to leave them running.

Before the first Case, create the authorized handbook at its final path with status `Draft/Running`. After every command and Case, update the artifacts in this order: command ledger and evidence, event journal, run-state checkpoint, machine results, then the matching handbook section. Each handbook update records the current `handbook_revision`, `last_synced_case`, actual result, evidence, and one next action. A `running` Case left by an interruption must be recovered as `Blocked` or rerun; it cannot be treated as `Pass`.

If a case fails, investigate only within the approved local scope. Do not silently broaden the target or change application code. Record the failure and stop the final-handbook gate until the required cases pass.

### 3a. Self-resolution and operator escalation

When a case cannot proceed because of an error, missing environment information, unclear behavior, unavailable dependency, or an operational decision:

1. Classify the obstacle and preserve the current command, inputs, output, logs, container state, and data observations.
2. Try at most three materially different, low-risk actions within the approved envelope. Prefer read-only inspection, health checks, log inspection, configuration comparison, and a narrowly scoped retry. Never repeat the same failed command without a new hypothesis or new evidence.
3. Stop self-resolution immediately when the next action would require new credentials, unknown business rules, a new service/data scope, destructive cleanup, code/configuration changes, or an operator-only action.
4. If the obstacle remains after the bounded attempts, or an operator-only input is required, write an `operator_request` checkpoint and enter `WAITING_FOR_OPERATOR_INPUT`.
5. Ask one concise, actionable request containing: blocker summary, Case/Failure ID, attempts already made, decisive evidence, exactly what information or action is needed, acceptable input format, and what will happen after the response.
6. Do not keep testing, guess missing values, or poll/retry while waiting. Keep the Case `Blocked` or `Waiting for input`.
7. When the operator responds, validate the input against the current project, approval envelope, and safety boundary before using it. Record the response and resume only from the persisted `next_action`.
8. If the operator declines, does not respond, or the input is invalid, keep the run `Blocked`, report the missing decision, and do not produce a passing handbook.

The retry budget is per symptom and per Case. A new symptom or new evidence may create a new bounded investigation, but it must not reset an unresolved loop silently.

### 3b. Diagnose failures and handle approved remediation

When a machine case fails or the observed result does not match the expectation:

1. Preserve the exact command, inputs, response, decisive log lines, container health, and database/Redis observations before changing state.
2. Confirm whether the failure is reproducible. Distinguish product behavior, test-data/setup error, environment/dependency failure, timing/flakiness, and assertion/expectation mismatch.
3. Trace the failure through the smallest relevant chain: caller/API, service logic, database, Redis/cache, message/event, downstream consumer, and read-back.
4. Produce a failure analysis containing: Case ID, severity, evidence, suspected root cause, alternative hypotheses, affected change points and legacy flows, proposed solution options, files/services/data that would change, risk, rollback, and a retest plan.
5. Stop before any fix, rebuild, restart, migration, test-data rewrite, or destructive retry. Ask the user to approve the exact remediation scope. Read-only diagnostics may continue only within the already approved local scope.
6. After explicit approval, make only the approved minimal change. Record the approval, changed targets, command/result, and new build or commit in the manifest.
7. Rebuild or restart only the approved local services, rerun the failed case, then rerun all directly affected legacy and cross-service regression cases. Do not convert a previously failed case to `Pass` without a successful retest and evidence.
8. If the proposed fix is rejected, ambiguous, unsafe, or still fails, keep the case `Fail` or `Blocked`, report the remaining evidence, and do not produce a final passing handbook.

Use a stable `F-*` failure ID and `X-*` remediation ID so the failure, approval, fix, and retest remain traceable across a resumed conversation.

### 3c. Recover long-running or interrupted tests

Use [references/run-state.md](references/run-state.md) for the state schema and recovery order. The allowed phases are:

`SCOPE_CHECK -> APPLICATION_ISOLATION -> LINK_INTEGRATION -> FAILURE_TRIAGE -> WAITING_FOR_FIX_APPROVAL -> RETEST -> REGRESSION -> PERSIST_RESULTS -> DONE`

When a turn resumes, a context window is compressed, or the process appears to have stopped:

1. Read `run-state.json`, the latest events from `event-journal.jsonl`, the change-scope manifest, and the latest machine results.
2. Verify the current repository commit, project rules, compose definition, and actual container state; stored state is workflow evidence, not proof that the current code or service is unchanged.
3. Reconcile the state with the latest evidence. If the current phase, Case, approval envelope, or next action cannot be established, stop and report `Recovery incomplete`.
4. Execute only the single persisted `next_action`. Do not replay completed Cases unless the state or environment check shows their evidence is invalid.
5. Checkpoint the recovery decision before continuing to the next Case.

Do not summarize a long run from memory. The state file and journal are the control record; the current repository and runtime are the authority for technical facts.

### 4. Apply the pass gate

The final handbook is `machine-validated` only when:

- every required affected application passes its application-isolation gate;
- every required affected application has a passing container-level changed-behavior functional case;
- no multi-application link case is marked runnable before its application prerequisites pass;
- all required new-feature cases pass;
- every identified affected legacy regression case passes;
- the change-scope manifest is `Complete` and its baseline, test version, source list, and revision are recorded;
- every confirmed change point maps to executed machine coverage and a manual scenario;
- every unknown impact is resolved or explicitly accepted as an uncovered risk;
- every failed case has either a successful approved remediation and retest, or is explicitly reported as an unresolved failure/blocker;
- approved remediation records identify the changed target, approval, retest Case ID, and regression evidence;
- the run state reaches `PERSIST_RESULTS` only after all required Cases and recovery decisions are recorded;
- the final state, event journal, machine results, and evidence paths are internally consistent;
- every manual Case can be followed from a clean local environment without relying on conversation memory; its variables, commands, expected outputs, pass rule, failure branch, and cleanup steps are complete;
- `command-ledger.md` contains every successful command used to build the handbook, with Case ID, working directory, exit code, output, evidence path, and execution time;
- the handbook has been updated after every completed Case and its final status is `Machine-validated/Done` only after the pass gate and cleanup succeed;
- no final handbook contains `<short cmd>`, `<short cmd or action>`, `<steps>`, `<docker command>`, `<short cleanup cmd>`, or an equivalent undefined action placeholder;
- cross-service data and read-back checks pass where relevant;
- the environment and test data were cleaned up or the remaining state is explicitly reported;
- no required case is marked skipped or blocked.

If the gate is not satisfied, output a machine-test failure report with the case matrix, exact blocker, evidence, and next action. The required `Draft/Running` handbook may remain incomplete or blocked, but it must never be labeled as a reliable final handbook.

### 5. Produce the handbook from evidence

Read [references/handbook-template.md](references/handbook-template.md) before creating the running handbook and again before closing it. Keep the handbook in Chinese unless the user requests another language.
Read [references/executable-manual-standard.md](references/executable-manual-standard.md) as the final actionability gate. The standard is binding for Windows `cmd.exe` commands, command-ledger provenance, variable initialization, Case step tables, failure branches, and cleanup verification.

The handbook must include:

- title, change scope, tested commit/build, execution time, environment, and limitations;
- a scope-completeness statement with baseline, test version, evidence sources, manifest revision, confirmed count, unknown count, and excluded areas;
- a machine-test summary table with every case ID, command/action, expected result, actual result, status, and evidence;
- an application-isolation table for each affected application, including container/dependency scope, health/configuration checks, local checks, and gate status;
- a multi-application link table showing prerequisite isolation Case IDs and link Case results;
- a failure and remediation log for every failed or unexpected case, including diagnosis, approved solution, changed scope, retest, and regression result;
- a run execution summary showing phase transitions, checkpoints, interruptions/recoveries, and the final `run-id` state;
- a traceability table from each change point to machine cases and manual cases;
- prerequisites and local-only safety notes;
- short, ordered startup and health-check steps;
- deterministic test-data preparation;
- manual new-feature scenarios;
- manual regression scenarios for all affected old behavior;
- failure, boundary, permission, idempotency, retry, and repeat-run scenarios when applicable;
- database/Redis verification steps using Docker commands;
- cleanup and reset steps;
- a result-recording section with Pass/Fail/Blocked/Not applicable semantics;
- known gaps and evidence-backed limitations.

Use only commands captured from successful machine execution and referenced by `command-ledger.md`, or mark the step `Blocked/待人员输入` with its exact missing input. Keep the manual usable by a person copying one step at a time: initialize variables first, include one Windows `cmd.exe` command per code block or numbered step, state the working directory and expected output, and provide a concrete next action for every failure. A prose verb such as “启动、准备、模拟、观察、检查、清理” is incomplete until paired with a command or fully specified UI action.

Persist the running and finalized handbook under the skill-local workspace described in [references/historical-reuse.md](references/historical-reuse.md). Create it before the first Case, update it after each Case, and close it in place by changing its status; do not regenerate it from memory at the end. Include all exact paths in the run's initial batch authorization; after that approval, do not request separate confirmation for those listed writes. Use Chinese basenames for user-visible Markdown documents. Update the project index and global catalog only after the corresponding artifact is written successfully.

After each completed run, extract reusable knowledge into the project experience record. Promote an item to the cross-project experience library only when it is generic, evidence-backed, sanitized, and states its applicability and invalidation conditions. Do not promote business-specific identifiers, credentials, customer data, or assumptions tied to one repository.

## Command rules

- Commands must be Windows `cmd.exe` syntax such as `cd /d`, `set`, `curl`, `docker`, and `docker compose`; do not provide PowerShell, Bash, WSL, or POSIX variants.
- Keep each command near or below 100 characters. Split long operations into short numbered commands and use short variables or a working-directory change. Do not hide a long command behind an unreadable one-liner.
- Database and Redis operations must run inside the relevant container with `docker exec` or `docker compose exec`. Do not use host-installed `mysql`, `psql`, `redis-cli`, or equivalent clients.
- Use read-only queries for verification when possible. For mutations, make the test-data prefix explicit and provide the matching cleanup command.
- Never embed real secrets in the handbook. Use repository-documented environment variables or `<PLACEHOLDER>` values and state exactly what the tester must supply.
- Preserve the tested command and a concise output excerpt in the machine-result table. If an output is too long, record the decisive line and where the full log was captured.
- For commands that reference the skill workspace, shorten the path with a target-specific variable when that keeps individual commands readable: on Windows use `set TD=%USERPROFILE%\.codex\skills\manual-e2e-test-handbook\workspace`; on Linux/macOS use `export TD="$HOME/.codex/skills/manual-e2e-test-handbook/workspace"`.
- Keep runtime state and journal records concise, append-only where possible, and free of secrets or full raw logs; link to sanitized evidence instead.

## Output and safety behavior

- Default to returning the handbook in the response. For persistent output, derive the exact target path from the `project-key`, feature/version, and `run-id`, include that path in the run's initial batch authorization, persist it in `run-state.json`, and register it in the project/global indexes for later reuse. A separately requested path outside that envelope requires confirmation.
- When persistent output is requested or required by this workflow, use the skill-local `workspace/` location by default rather than the tested repository.
- Do not run containers or mutate data while merely drafting a plan or explaining the skill.
- Do not modify application code, Docker configuration, migrations, or test fixtures as part of this skill unless the user separately requests that work.
- A machine-test failure is not permission to modify application code, Docker configuration, migrations, test fixtures, or data. Request explicit approval for the exact fix before any such action.
- Never persist secrets, access tokens, personal data, production data, or unredacted sensitive logs. Store only the smallest sanitized evidence needed to support a result.
- Do not delete or overwrite the skill-local workspace during skill maintenance. A skill replacement or reinstall may not preserve runtime records, so report that portability limitation and recommend a user-controlled backup when the accumulated knowledge matters.
- If cleanup fails, report the remaining containers/data explicitly and do not claim a clean run.


