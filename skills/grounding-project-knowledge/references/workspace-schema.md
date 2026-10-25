# Workspace Navigation Schema

Read this reference before creating or changing machine-local project registration or cross-project routing records.

## Storage

```text
knowledge/projects/_workspace/
|-- projects/<project-key>.json
`-- routes/<route-id>.json
```

The reserved `_workspace` directory remains inside the existing validated
knowledge-data write boundary. Records are retained by status; automatic
maintenance never deletes durable records.

## Workspace Project

Use `workspace-register` rather than constructing this record manually. It
derives the project key, normalized Git remote, absolute root, `.codegraph/`
presence, and `AGENTS.md` pointer/hash from the current machine.

| Field | Contract |
|---|---|
| `schema_version` | Integer `1` |
| `record_type` | `workspace-project` |
| `project_key` | Deterministic key derived from Git remote or absolute root |
| `display_name` | Current repository label |
| `root` | Current absolute repository path |
| `remote` | Normalized Git remote or `null` |
| `aliases` | Non-empty operator search terms |
| `domains` | Non-empty product or technical domains |
| `purpose` | Short operator-provided navigation description |
| `operator_hints` | Navigation leads; never current-code proof |
| `entry_points` | One or more local roots or useful nested source roots for the same Git identity |
| `codegraph` | Absolute `.codegraph` path and observed presence |
| `policy` | Absolute `AGENTS.md` path, observed existence, and SHA-256 when present |
| `metadata_basis` | `filesystem-and-git` |
| `verified_at` | UTC ISO-8601 timestamp ending in `Z` |
| `status` | `current`, `needs-reverification`, or `retired` |

The policy hash only detects change. Always reopen the current `AGENTS.md`
before work. An alias, purpose, domain, or hint is operator input and must not
be presented as a code fact.

Each entry point stores its absolute `path`, aliases, domains, purpose, hints,
`.codegraph/` observation, and `AGENTS.md` pointer/hash. Multiple paths sharing
one normalized Git remote remain one project record with multiple entry points;
registering a nested source root must not overwrite its repository root.

## Workspace Route

Route candidates accepted by `workspace-upsert-route` contain all fields below
except `route_id`, which the store derives deterministically.

| Field | Contract |
|---|---|
| `schema_version` | Integer `1` |
| `record_type` | `workspace-route` |
| `route_id` | Stored records only; deterministic 20-character identifier |
| `title` | Short retrieval label |
| `triggers` | Non-empty product, API, feature, or symptom terms |
| `project_keys` | Ordered registered projects to inspect |
| `guidance` | Concise navigation direction |
| `basis` | `operator-provided` or `code-verified` |
| `evidence` | Empty for operator routes; current evidence from every project for code-verified routes |
| `verified_at` | UTC ISO-8601 timestamp ending in `Z` |
| `status` | `current`, `needs-reverification`, or `retired` |

Each code-verified evidence object contains `project_key`, project-relative
`path`, precise `symbol`, one-based `line_start` and `line_end`, and the current
whole-file `sha256`. Documentation files cannot prove a technical route.

## Commands

Run `scripts/knowledge_store.py --help` and the relevant subcommand help for
exact arguments:

- `workspace-register`: derive or refresh a repository record.
- `workspace-query`: retrieve matching projects and routes.
- `workspace-upsert-route`: validate and atomically store one route candidate.
- `workspace-revalidate`: detect missing roots, remote changes, `.codegraph/`
  changes, or changed repository rules; use `--check-only` for read-only work.
- `validate`: validate project facts and workspace records together.

## Evidence Boundary

- Filesystem existence and Git metadata establish where a repository is now.
- Current code from every named project is required for a technical relationship.
- Operator-provided routing is a search lead, not an implementation fact.
- Stored rules are never authoritative; only the current referenced rule file is.
- Stored navigation never replaces current code inspection or CodeGraph.


