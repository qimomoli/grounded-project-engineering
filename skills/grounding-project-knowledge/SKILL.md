---
name: grounding-project-knowledge
description: Use when locating local repositories or understanding, designing, changing, debugging, testing, or reviewing code where project routes, rules, structure, behavior, dependencies, data flow, or implementation facts may be reused across work.
---

# Grounding Project Knowledge

## Core Contract

Recover useful project facts from current code and maintain local workspace navigation for later work. Stored knowledge is an index into current evidence, never a substitute for reading the latest code or repository rules.

Only executable or machine-parsed project artifacts can establish a fact: implementation source, runtime configuration, build definitions, migrations, and interface definitions. Tests may corroborate behavior. README files, Wiki pages, tickets, chats, commit messages, comments, and knowledge from another project are search leads only.

## Workspace Routing

When the repository is unknown or work may cross projects:

1. Run `workspace-revalidate --check-only` for read-only tasks; otherwise run `workspace-revalidate`.
2. Run `workspace-query --text <terms>` with the user's domain, product, API, or symptom terms. Load only matching records.
3. Recheck the selected root on disk. Read its current `AGENTS.md` directly when present; the stored policy path and hash are only a change detector.
4. Treat `operator-provided` routes and hints as navigation leads. Verify technical relationships against current code in every involved repository.
5. Register newly encountered repositories and maintain reusable routes automatically. Read [references/workspace-schema.md](references/workspace-schema.md) before writing workspace records.

If the selected root contains `.codegraph/`, use CodeGraph before text search for code locations and call paths. CodeGraph analyzes current code; workspace knowledge does not replace it.

## Project Fact Workflow

1. Resolve the current project with `scripts/knowledge_store.py resolve-project`.
2. Run `revalidate` before retrieval; source changes downgrade affected entries to `needs-reverification`. If the user's task is explicitly read-only, run `revalidate --check-only`, treat reported entries as stale, and verify them directly without writing.
3. Query only terms, paths, and symbols relevant to the current task. Do not load the whole store.
4. Verify every retrieved claim against current source before relying on it.
5. Complete the project task using current code as the authority.
6. When the work establishes a reusable fact, construct a schema-valid candidate and run `upsert --candidate -`, supplying JSON on stdin. Do not create an unvalidated staging file.
7. Report every automatic maintenance action using the contract below without asking for confirmation.

Read [references/knowledge-schema.md](references/knowledge-schema.md) before constructing or changing an entry. Run the script with `--help` for exact arguments.

## Decision Rules

| Situation | Action |
|---|---|
| Current source supports the claim and hashes match | Use and maintain `current` |
| Source changed or disappeared | Use `needs-reverification`; do not rely on the claim |
| Only documentation, comments, memory, or another project supports it | Treat as a lead; do not store as a fact |
| A fact is no longer part of the system | Preserve it as `retired`; never delete automatically |
| Validation, path safety, or writing fails | Stop knowledge maintenance, report it, continue the main task |

## Maintenance Report

When this skill writes knowledge data, the same user-visible response must contain:

```text
知识库维护：
- 项目知识|工作区项目|跨项目入口：新增|刷新|标记待复核|退役 <title> (<entry_id|project_key|route_id>)
```

List each maintained record. Report validation or write failures instead of implying maintenance succeeded. Omit this section only when no knowledge-data write occurred.

## Write Boundary

Automatic writes are limited to schema-validated data under this skill's `knowledge/projects/**`, including the reserved `_workspace` navigation directory. The exception does not cover `SKILL.md`, `agents`, `scripts`, `references`, schema changes, Git, network access, project source, or external systems. Platform permission prompts still apply.

## Example

A README says controller A calls legacy service B, while current code shows A calling dispatcher C. Store only the A-to-C claim with the current source path, symbol, line range, and file SHA-256. The README statement remains a lead and never becomes a project fact.

## Common Mistakes

- Treating a stored claim as proof without reopening current source.
- Saving task narration, temporary observations, or large source excerpts.
- Copying a fact across project keys.
- Updating evidence hashes without re-reading the referenced code.
- Treating a stored path, route, or policy hash as proof that the repository or rule is unchanged.
- Omitting the maintenance report because knowledge writes were incidental to the main task.


