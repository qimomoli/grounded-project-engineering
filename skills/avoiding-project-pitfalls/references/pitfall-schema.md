# Project Pitfall Schema

Read this reference before constructing or changing a project pitfall record.

## Storage And Identity

Each project is stored under `knowledge/projects/<project-key>/`:

```text
project.json
entries/<entry-id>.json
```

The project key comes from a credential-free normalized Git origin when available, otherwise from the normalized absolute project root. Different projects never merge. The entry ID is derived from the project key, normalized trigger conditions, and affected scope, so an update to the same risk replaces the same record even if its title changes.

An `upsert` candidate omits `entry_id` and `project_key`; the store injects both. A durable record must contain them and match their deterministic values.

## Record Fields

| Field | Type | Contract |
|---|---|---|
| `schema_version` | integer | Must equal `1` |
| `entry_id` | string | Store-generated deterministic ID; omitted from candidates |
| `project_key` | string | Store-generated current project key; omitted from candidates |
| `title` | string | Short retrieval label |
| `symptom` | string | Observable failure, regression, or misleading behavior |
| `trigger_conditions` | string array | Conditions under which the risk was observed or is suspected |
| `affected_scope` | string array | Existing project-relative files; must cover every `related_code.path` |
| `root_cause` | string | Code-supported cause; may be empty only for `candidate` |
| `historical_evidence` | object array | Observed failure or runtime evidence |
| `related_code` | object array | Current or historically verified code anchors |
| `validated_resolution` | string | Demonstrated fix or avoidance; may be empty only for `candidate` |
| `current_reverification` | string array | Required current-code inspections or tests before use |
| `observed_at` | string | Valid UTC ISO-8601 timestamp ending in `Z` |
| `status` | string | `candidate`, `verified-history`, or `obsolete` |

Each historical evidence object contains:

| Field | Type | Contract |
|---|---|---|
| `kind` | string | `test-failure`, `reproduction`, `runtime-observation`, or `log-observation` |
| `summary` | string | Concise observation without raw logs, secrets, or personal data |
| `observed_at` | string | Valid UTC ISO-8601 timestamp ending in `Z` |

Each related code object contains:

| Field | Type | Contract |
|---|---|---|
| `path` | string | Existing project-relative file also listed in `affected_scope` |
| `symbol` | string | Non-empty function, class, key, target, or other precise anchor |
| `line_start` | integer | One-based first line |
| `line_end` | integer | One-based final line, not beyond the file |
| `sha256` | string | Lowercase SHA-256 of the complete file |

Common documentation extensions such as `.md`, `.rst`, and `.txt` cannot be `related_code`.

## Promotion And Lifecycle

- `candidate` is a reference-only suspicion. It may contain incomplete cause, observation, code, or resolution fields, but every required key must be present and `current_reverification` must be actionable.
- Promote to `verified-history` only when the record has an observed failure or runtime result, a code-supported root cause, and a validated resolution.
- A commit message, README, issue, recollection, or another project cannot satisfy those requirements.
- When related code changes or disappears, `revalidate` preserves the record as `obsolete`. This means it is no longer applicable to the current checkout without new verification; it does not erase the historical observation.
- Never automatically delete a durable record or invent additional lifecycle states.

Every query result includes `reference_notice`. Preserve that qualification when presenting a result. A record must never be labeled a current fact.

## Complete Candidate Example

```json
{
  "schema_version": 1,
  "title": "Duplicate delivery can create duplicate orders",
  "symptom": "Concurrent delivery created two orders for one business key",
  "trigger_conditions": [
    "two deliveries share one business key"
  ],
  "affected_scope": [
    "src/order_consumer.py"
  ],
  "root_cause": "Order creation previously ignored a failed idempotency acquisition",
  "historical_evidence": [
    {
      "kind": "test-failure",
      "summary": "Concurrency regression test observed two created orders",
      "observed_at": "2026-10-23T00:00:00Z"
    }
  ],
  "related_code": [
    {
      "path": "src/order_consumer.py",
      "symbol": "OrderConsumer.handle",
      "line_start": 12,
      "line_end": 18,
      "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    }
  ],
  "validated_resolution": "Return when the atomic idempotency acquisition fails",
  "current_reverification": [
    "Inspect OrderConsumer.handle and IdempotencyStore.tryAcquire",
    "Run the concurrent duplicate-delivery regression test"
  ],
  "observed_at": "2026-10-23T00:00:00Z",
  "status": "verified-history"
}
```

Replace the illustrative path, lines, hash, observations, and resolution with values verified from the actual project before `upsert`.

## Workspace Cross-Project Records

Cross-project records are stored separately under:

```text
knowledge/projects/_workspace/pitfalls/<pitfall-id>.json
```

They use `schema_version: 1` and `record_type: "cross-project-pitfall"`, with
the following additional fields:

| Field | Type | Contract |
|---|---|---|
| `pitfall_id` | string | Store-generated ID from category, trigger conditions, affected boundaries, and related project keys |
| `category` | string | `general` or `cross-project-development` |
| `affected_boundaries` | string array | Protocol, data, deployment, or other cross-project boundaries; non-empty |
| `related_projects` | string array | Project keys resolved from current project roots; unique and non-empty |
| `applicability` | string | Conditions under which the historical lesson may be relevant |
| `invalidation_conditions` | string array | Conditions that make the lesson stale or inapplicable |

Each workspace `related_code` object adds `project_key` and keeps the same
project-relative `path`, symbol, line range, and complete-file SHA-256 contract
as project records. A `general` record may reference one project. A
`cross-project-development` record must reference at least two projects; a
`verified-history` record must have code anchors from every related project.
The supplied `--project-root` values are checked against those keys before
writing or revalidating.

Workspace records are reference-only. `global-query` always adds
`reference_notice`, and `global-revalidate` marks a record `obsolete` when a
verified code anchor changes or disappears. Missing project roots are reported
as unverified rather than silently treated as current. Do not copy a cause or
resolution from one repository to another without fresh code or runtime
evidence in the affected repositories.

## CLI Sequence

Use the available Python 3 runtime. On this machine it is:

```text
python
```

Run `resolve-project`, then `revalidate`, then a filtered `query`. For an explicitly read-only task, use `revalidate --check-only`. For maintenance, run `upsert --project-root <root> --candidate -` and send one JSON object on stdin. For cross-project maintenance, pass every involved root to `global-revalidate` or `global-upsert` by repeating `--project-root`, and use `global-query` for retrieval. Validation failure returns exit code `2` without changing the previous record.

Do not store raw logs, source excerpts, secrets, tokens, credentials, or personal data. Secret-pattern checks reduce accidental capture but are not a complete secret scanner; inspect candidate content before upsert.


