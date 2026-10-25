---
name: avoiding-project-pitfalls
description: Use when designing, coding, debugging, testing, or reviewing a project where previously observed mistakes, misleading assumptions, regressions, fragile behavior, or troubleshooting lessons may be relevant but must be rechecked against current code.
---

# Avoiding Project Pitfalls

## Core Contract

Use stored pitfalls to generate checks and hypotheses, never current facts. Before a pitfall affects a design, diagnosis, code change, test, or review finding, verify it against the current project's code and, when needed, current runtime or test evidence.

A `verified-history` record proves only that the issue occurred under its recorded conditions. It does not prove that the same root cause or remedy applies now. If current code cannot confirm relevance, label the record unconfirmed and do not change code because of it.

## Workflow

1. Resolve the current project with `scripts/pitfall_store.py resolve-project`.
2. Run `revalidate` before retrieval. For an explicitly read-only task, use `revalidate --check-only` and do not write.
3. For a cross-project task, run `global-revalidate` with every involved project root, then use `global-query` for symptoms, boundaries, categories, and statuses. Do not load the whole store.
4. Turn every result into a concrete inspection or test checklist. Keep the returned `reference_notice` visible in reasoning.
5. Inspect current implementation, call paths, configuration, dependencies, and concurrency or failure boundaries in every affected project. If `.codegraph/` exists at a repository root, use CodeGraph before text search for code location and call paths.
6. Use a pitfall only after current code confirms its preconditions and relevant mechanism. A cross-project record is a search lead across repositories, never proof that the same cause or fix applies in each repository.
7. After the task produces reusable evidence, build one schema-valid candidate and run `upsert --candidate -` or `global-upsert --candidate -` with JSON on stdin. Do not create an unvalidated staging file.
8. Report every automatic maintenance action using the contract below without asking for confirmation.

Read [references/pitfall-schema.md](references/pitfall-schema.md) before constructing or changing a record. Run the script with `--help` for exact arguments.

## Evidence And Status Rules

| Situation | Action |
|---|---|
| A plausible risk lacks both observed failure evidence and a code-supported root cause | Store or retain `candidate`; present only as a hypothesis |
| Failure or runtime evidence, code root cause, and validated resolution are all present | Store `verified-history`; still recheck current code before use |
| Related current code changed or disappeared | Preserve as `obsolete`; do not delete or apply it automatically |
| Another project has the same symptom | Use only as a search lead; never copy its root cause or resolution into this project |
| A cross-project record names multiple repositories | Recheck every named repository and its current compatibility boundary before relying on it |
| Current code cannot confirm applicability | Do not base a modification or definite conclusion on the record |
| Validation, path safety, or writing fails | Stop pitfall maintenance, report it, continue the main task |

## Maintenance Report

When this skill writes knowledge data, the same user-visible response must contain:

```text
避坑库维护：
- 新增|刷新|标记待复核|退役 <title> (<entry_id>)
```

List each maintained record. Report validation or write failures instead of implying maintenance succeeded. Omit this section only when no knowledge-data write occurred.

For workspace records, identify the category explicitly:

```text
避坑库维护：
- 跨项目通用坑：新增|刷新|标记待复核|退役 <title> (<pitfall_id>)
- 跨项目开发坑：新增|刷新|标记待复核|退役 <title> (<pitfall_id>)
```

## Write Boundary

Automatic writes are limited to schema-validated data under this skill's `knowledge/projects/**`. Never automatically modify `SKILL.md`, `agents`, `scripts`, `references`, schemas, Git state, project source, network services, or external systems. Never delete a durable record. Platform permission prompts and an explicit user read-only request still apply.

Workspace records live under `knowledge/projects/_workspace/pitfalls/`. A
`general` record is a reusable, de-identified technical trap grounded in code
from at least one project. A `cross-project-development` record covers a
boundary such as a protocol, migration, compatibility window, or upstream /
downstream deployment and must bind verified-history code anchors from at least
two projects. Both categories remain reference-only and must state applicability
and invalidation conditions.

## Example

A historical record says duplicate orders were fixed by synchronizing a controller. The current code publishes to a queue and creates orders in a consumer guarded by an idempotency store. Treat the old record as a prompt to inspect message redelivery, the consumer, the atomic acquisition, and the database constraint. Do not add a controller lock unless current code and failure evidence establish that boundary.

## Common Mistakes

- Repeating a historical root cause as though it describes the current checkout.
- Applying another project's fix because the symptom text matches.
- Promoting a record from a commit message, README, or recollection without observed failure and current code evidence.
- Updating hashes without rereading the referenced code.
- Inventing new statuses, shared cross-project records, scheduled maintenance, or commands outside this skill's schema and CLI.
- Omitting the maintenance report because the pitfall update was incidental to the main task.


