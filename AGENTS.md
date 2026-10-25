# Repository Instructions

## CodeGraph

If a consumer project contains a `.codegraph/` directory at its root, use
CodeGraph before text search when locating symbols, call paths, or current
implementation details.

## File Write Confirmation

Before creating, editing, overwriting, deleting, renaming, moving, publishing,
or otherwise mutating a file or external resource, restate the exact scope,
targets, intended change, indirect effects, assumptions, and open questions;
then wait for explicit confirmation. Read-only inspection may proceed without
confirmation.

## Self-Maintaining Knowledge Exception

schema-validated knowledge-data creation, update, atomic replacement, and
tool-owned temporary cleanup may proceed without a new confirmation only under
these bounded paths:

- `grounding-project-knowledge\knowledge\projects\**`
- `avoiding-project-pitfalls\knowledge\projects\**`

The target must remain inside the selected skill's knowledge root and must not
escape through `..`, a symbolic link, or a Windows reparse point. This exception
does not authorize changes to `SKILL.md`, `agents`, `scripts`, `references`,
schemas, Git state, source repositories, network services, or external systems,
and it does not bypass platform permission prompts.

Never delete durable knowledge records; mark them obsolete or retired instead.
