---
name: confirm-before-work
description: Use before any direct or indirect local or external side effect, requiring the assistant to restate the exact scope and wait for explicit user confirmation.
---

# Confirm Before Work

## Overview
Use this skill whenever the next action may create, edit, overwrite, delete, rename,
move, publish, send, restart, provision, or otherwise cause a consequential local
or external side effect.

## Core Rule
Before the first side effect:

1. Stop before running the side-effect-capable action.
2. State the action you are about to take.
3. List the target files, repositories, services, resources, endpoints, or
   bounded target patterns.
4. State the intended change and any likely indirect side effects.
5. State boundaries, assumptions, and open questions.
6. Ask for explicit confirmation.
7. Wait for a clear affirmative response before acting.

The user's original request is not, by itself, confirmation of the
understanding check. The check exists to confirm that the proposed side effect
and its scope match the request.

## Scope
Apply this to direct and indirect local or external mutations, including:

- Creating, editing, overwriting, deleting, renaming, or moving files.
- Commands that generate or update lockfiles, snapshots, reports, coverage data,
  build output, caches, indexes, or other artifacts.
- Formatters, code generators, migrations, and tests that can modify the
  workspace.
- Repository metadata or working-tree changes, such as operations that alter
  the index or tracked files.
- Batch operations whose exact file list is discovered only while they run.
- Outbound network requests that change or submit external state.
- Database inserts, updates, deletes, migrations, and schema changes.
- Cloud-resource provisioning, updates, deletion, or permission changes.
- Service starts, stops, restarts, deployments, and runtime configuration changes.
- Sending messages, publishing comments, creating appointments, or other
  representational communication.
- Git pushes, pull requests, releases, package publication, and other code
  publication.

Treat an action as side-effect-capable when its effects are uncertain. Inspect
or explain the command first, then ask before running it if it may persist
anything, change state, or affect an external system.

The following are normally read-only and do not need confirmation:

- Reading files, searching, listing, and inspecting status or diffs.
- Reasoning, drafting, summarizing, or explaining in chat.
- Commands that are known to be read-only and have no generated output.
- Read-only network, database, cloud, service, or repository inspection that
  does not change state or transmit user data.

If a supposedly read-only command may create logs, caches, temporary files,
change state, or transmit data, treat it as a side effect.

## Self-Maintaining Knowledge Exception

No confirmation is required only for schema-validated knowledge-data creation,
update, atomic replacement, and cleanup of temporary files created by the same
operation under these exact roots:

- `grounding-project-knowledge\knowledge\projects\**`
- `avoiding-project-pitfalls\knowledge\projects\**`

The target must resolve inside one of those roots. Reject `..`, symbolic-link,
or Windows reparse point escapes. The exception permits durable knowledge
records to be created or updated, but not deleted; retire or obsolete them by
status instead. It does not cover `SKILL.md`, `agents/**`, `scripts/**`,
`references/**`, schemas, Git actions, network access, source repositories,
external systems, or any other file. Cleanup is limited to tool-owned `.tmp`
files created by the same atomic write. This collaboration exception does not
bypass platform permission prompts or sandbox restrictions.

## Authorization Boundaries
A confirmation authorizes only the action, targets, and boundaries named in
the immediately preceding understanding check.

Ask again before proceeding when any of these change:

- A new file, directory, repository, service, resource, endpoint, or external
  system is involved.
- The proposed content or operation becomes materially different.
- The implementation needs a broader file pattern or a destructive action.
- A command introduces an unlisted generated artifact, transmission, or other
  side effect.
- The user's response is ambiguous, conditional, or does not clearly approve
  the proposed action.

Do not infer approval from silence, a topic change, or the fact that the user
originally asked for the task. When in doubt, pause and ask.

## Understanding Format
Use this concise structure:

- Action I am about to take
- Target file(s), directory(ies), repository(ies), service(s), resource(s),
  endpoint(s), or bounded pattern(s)
- Intended change
- Potential indirect side effects
- Boundary and assumptions
- What is still unclear, if anything
- Confirmation request

The target list may use a clearly bounded pattern such as `src/**/*.ts`. For
path-like targets, `*` matches within one path segment and never crosses a
directory boundary; `**` may match multiple path segments. Reject targets with
`..` path segments and reject unbounded target patterns such as `*`, `**`, or
`**/*`.

## Examples

### Direct edit

```text
File action I am about to take:
- Edit an existing Markdown file.

Target file(s):
- README.md

Intended change:
- Add installation instructions.

Potential indirect side effects:
- None expected.

Boundary and assumptions:
- I will only change the installation section.
- I will not change project behavior or other files.

What is still unclear:
- Nothing.

Please confirm before I perform this action.
```

### Command with an implicit write

```text
File action I am about to take:
- Run the formatter on the selected source files.

Target file(s):
- src/**/*.ts

Intended change:
- Apply the repository formatter to existing source files.

Potential indirect side effects:
- The formatter may update generated formatting metadata or a lockfile if
  the project tooling does so.

Boundary and assumptions:
- I will not modify files outside the listed source pattern or generated
  artifacts identified before execution.

What is still unclear:
- Nothing.

Please confirm before I run the formatter.
```

### External side effect

Before sending a request, changing a database or cloud resource, restarting a
service, sending a message, pushing code, or opening a pull request, the agent
should identify the destination, operation, intended payload or state change,
and likely side effects. Read-only inspection is allowed when it does not
change state or transmit user data.

### Scope change after approval

If the user approved `README.md` but implementation reveals that
`docs/install.md` must also change, stop and present a new understanding check
for the additional file. The first approval does not cover the new target.
The same rule applies to a new operation, destination, external system, or
side-effect category.

## Conformance Evaluations

The repository includes a dependency-free evaluator and checked-in cases:

```powershell
python -B .\evals\validate.py --cases .\evals\cases.json
```

See `evals/README.md` for the trace format and runtime adapter contract.

## Common Mistakes

- Performing a side effect before presenting the understanding check.
- Treating the user's initial task request as approval of an unreviewed plan.
- Listing only source files while omitting generated artifacts, metadata, or
  external destinations.
- Running a formatter, test, build, migration, or generator without checking
  whether it writes files.
- Expanding the target set after approval without asking again.
- Treating an ambiguous response as permission.
- Hiding an unknown scope behind `**/*` or another unbounded pattern.
- Treating this skill as a sandbox. It is a collaboration rule;
  enforcement still depends on the agent and its tool environment.


