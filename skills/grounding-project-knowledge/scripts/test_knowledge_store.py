from __future__ import annotations

import copy
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

try:
    import knowledge_store as store
except ModuleNotFoundError as exc:
    store = None
    IMPORT_ERROR = exc
else:
    IMPORT_ERROR = None


class KnowledgeStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertIsNone(IMPORT_ERROR, f"knowledge_store implementation missing: {IMPORT_ERROR}")
        self.temp = tempfile.TemporaryDirectory(prefix="codex-project-knowledge-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.project = self.base / "project"
        self.knowledge_root = self.base / "knowledge" / "projects"
        source = self.project / "src" / "handler.py"
        source.parent.mkdir(parents=True)
        source.write_text("def handle():\n    return service.run()\n", encoding="utf-8")
        self.source = source
        self.identity = store.resolve_project(self.project)

    def entry(self, *, title: str = "Request enters service", symbol: str = "handle") -> dict:
        return {
            "schema_version": 1,
            "kind": "call-flow",
            "title": title,
            "claim": "handle() directly calls service.run()",
            "scope": ["src/handler.py"],
            "evidence": [
                {
                    "kind": "source",
                    "path": "src/handler.py",
                    "symbol": symbol,
                    "line_start": 1,
                    "line_end": 2,
                    "sha256": store.sha256_file(self.source),
                }
            ],
            "verified_at": "2026-10-23T00:00:00Z",
            "status": "current",
        }

    def test_remote_identity_ignores_credentials_and_dot_git(self) -> None:
        left = store.normalize_remote("https://user:token@example.com/acme/demo.git")
        right = store.normalize_remote("git@example.com:acme/demo.git")
        self.assertEqual("example.com/acme/demo", left)
        self.assertEqual(left, right)
        self.assertNotIn("token", left)

    def test_path_identity_is_stable_without_remote(self) -> None:
        first = store.resolve_project(self.project)
        second = store.resolve_project(self.project)
        self.assertEqual(first.key, second.key)
        self.assertNotIn(str(self.project), first.key)

    def test_current_entry_requires_source_evidence(self) -> None:
        entry = self.entry()
        entry["evidence"] = []
        with self.assertRaises(store.ValidationError):
            store.validate_entry(entry, self.identity.key, self.project)

    def test_document_or_comment_only_evidence_is_rejected(self) -> None:
        for evidence_kind in ("documentation", "comment"):
            entry = self.entry()
            entry["evidence"][0]["kind"] = evidence_kind
            with self.subTest(evidence_kind=evidence_kind):
                with self.assertRaises(store.ValidationError):
                    store.validate_entry(entry, self.identity.key, self.project)

    def test_entry_path_cannot_escape_knowledge_root(self) -> None:
        outside = self.knowledge_root / ".." / "SKILL.md"
        with self.assertRaises(store.PathBoundaryError):
            store.ensure_within(outside, self.knowledge_root)
        self.assertFalse(outside.exists())

    def test_upsert_is_deterministic_and_does_not_duplicate(self) -> None:
        first = store.upsert_entry(self.entry(), self.project, self.knowledge_root)
        second = store.upsert_entry(self.entry(), self.project, self.knowledge_root)
        self.assertEqual(first, second)
        self.assertEqual(1, len(list(first.parent.glob("*.json"))))

    def test_changed_source_hash_marks_entry_for_reverification(self) -> None:
        path = store.upsert_entry(self.entry(), self.project, self.knowledge_root)
        self.source.write_text("def handle():\n    return replacement.run()\n", encoding="utf-8")
        result = store.revalidate_entries(self.project, self.knowledge_root)
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual("needs-reverification", payload["status"])
        self.assertEqual(1, result["changed"])

    def test_deleted_source_marks_entry_for_reverification(self) -> None:
        path = store.upsert_entry(self.entry(), self.project, self.knowledge_root)
        self.source.unlink()
        try:
            result = store.revalidate_entries(self.project, self.knowledge_root)
        except store.ValidationError as exc:
            self.fail(f"revalidate must tolerate missing evidence files: {exc}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual("needs-reverification", payload["status"])
        self.assertEqual(1, result["changed"])

    def test_query_filters_by_project_status_path_and_symbol(self) -> None:
        store.upsert_entry(self.entry(), self.project, self.knowledge_root)
        other = self.entry(title="Different flow", symbol="other")
        store.upsert_entry(other, self.project, self.knowledge_root)
        results = store.query_entries(
            self.identity.key,
            self.knowledge_root,
            {"status": "current", "path": "src/handler.py", "symbol": "handle"},
        )
        self.assertEqual(["Request enters service"], [item["title"] for item in results])

    def test_atomic_write_preserves_previous_file_on_validation_failure(self) -> None:
        path = store.upsert_entry(self.entry(), self.project, self.knowledge_root)
        original = path.read_bytes()
        invalid = copy.deepcopy(self.entry())
        invalid["evidence"][0]["sha256"] = "0" * 64
        with self.assertRaises(store.ValidationError):
            store.upsert_entry(invalid, self.project, self.knowledge_root)
        self.assertEqual(original, path.read_bytes())
        self.assertEqual([], list(path.parent.glob("*.tmp")))

    def test_secret_like_values_are_rejected(self) -> None:
        entry = self.entry()
        secret = "sk_1234567890abcdefghijkl"
        entry["claim"] = f"credential={secret}"
        with self.assertRaises(store.ValidationError) as caught:
            store.upsert_entry(entry, self.project, self.knowledge_root)
        self.assertNotIn(secret, str(caught.exception))

    def test_candidate_can_be_loaded_from_stdin_without_staging_file(self) -> None:
        candidate = self.entry()
        self.assertTrue(hasattr(store, "load_candidate"), "load_candidate must support stdin")
        loaded = store.load_candidate("-", io.StringIO(json.dumps(candidate)))
        self.assertEqual(candidate, loaded)
        self.assertEqual([], list(self.knowledge_root.rglob("*")))

    def test_read_only_revalidation_reports_stale_without_writing(self) -> None:
        path = store.upsert_entry(self.entry(), self.project, self.knowledge_root)
        original = path.read_bytes()
        self.source.write_text("def handle():\n    return replacement.run()\n", encoding="utf-8")

        result = store.revalidate_entries(self.project, self.knowledge_root, write=False)

        self.assertEqual(original, path.read_bytes())
        entry_id = json.loads(original)["entry_id"]
        self.assertEqual(
            {"checked": 1, "changed": 0, "would_change": 1, "stale_entries": [entry_id]},
            result,
        )

    def test_persisted_entry_requires_generated_identity_fields(self) -> None:
        candidate = self.entry()
        store.validate_entry(candidate, self.identity.key, self.project)
        with self.assertRaises(store.ValidationError):
            store.validate_entry(candidate, self.identity.key, self.project, stored=True)

    def test_evidence_line_end_cannot_exceed_file_length(self) -> None:
        entry = self.entry()
        entry["evidence"][0]["line_end"] = 3
        with self.assertRaises(store.ValidationError):
            store.validate_entry(entry, self.identity.key, self.project)

    def test_evidence_symbol_must_be_non_empty(self) -> None:
        entry = self.entry()
        entry["evidence"][0]["symbol"] = "  "
        with self.assertRaises(store.ValidationError):
            store.validate_entry(entry, self.identity.key, self.project)

    def test_kind_must_be_a_supported_knowledge_category(self) -> None:
        entry = self.entry()
        entry["kind"] = "anything-goes"
        with self.assertRaises(store.ValidationError):
            store.validate_entry(entry, self.identity.key, self.project)

    def test_verified_at_must_be_utc_iso_8601(self) -> None:
        for value in ("yesterday", "2026-10-23T08:00:00+08:00", "2026-10-23"):
            entry = self.entry()
            entry["verified_at"] = value
            with self.subTest(value=value):
                with self.assertRaises(store.ValidationError):
                    store.validate_entry(entry, self.identity.key, self.project)

    def test_scope_requires_existing_files_and_covers_evidence(self) -> None:
        missing = self.entry()
        missing["scope"] = ["src/missing.py"]
        with self.assertRaises(store.ValidationError):
            store.validate_entry(missing, self.identity.key, self.project)

        uncovered = self.entry()
        uncovered["scope"] = []
        other = self.project / "src" / "other.py"
        other.write_text("VALUE = 1\n", encoding="utf-8")
        uncovered["scope"] = ["src/other.py"]
        with self.assertRaises(store.ValidationError):
            store.validate_entry(uncovered, self.identity.key, self.project)

    def test_readme_cannot_be_disguised_as_source_evidence(self) -> None:
        readme = self.project / "README.md"
        readme.write_text("The handler calls a legacy service.\n", encoding="utf-8")
        entry = self.entry()
        entry["scope"] = ["README.md"]
        entry["evidence"][0].update(
            {
                "path": "README.md",
                "symbol": "legacy note",
                "line_start": 1,
                "line_end": 1,
                "sha256": store.sha256_file(readme),
            }
        )
        with self.assertRaises(store.ValidationError):
            store.validate_entry(entry, self.identity.key, self.project)

    def test_materially_different_claim_gets_a_distinct_entry(self) -> None:
        first = store.upsert_entry(self.entry(), self.project, self.knowledge_root)
        changed = self.entry()
        changed["claim"] = "handle() calls replacement.run() when dispatching"
        second = store.upsert_entry(changed, self.project, self.knowledge_root)
        self.assertNotEqual(first, second)
        self.assertEqual(2, len(list(first.parent.glob("*.json"))))

    def test_validate_store_runs_full_schema_validation(self) -> None:
        path = store.upsert_entry(self.entry(), self.project, self.knowledge_root)
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["evidence"][0]["symbol"] = ""
        path.write_text(json.dumps(payload), encoding="utf-8")
        with self.assertRaises(store.ValidationError):
            store.validate_store(self.knowledge_root, self.project)

    def test_existing_project_metadata_is_not_rewritten(self) -> None:
        first = store.upsert_entry(self.entry(), self.project, self.knowledge_root)
        project_path = first.parents[1] / "project.json"
        before = project_path.stat().st_mtime_ns
        os.utime(project_path, ns=(before - 1_000_000, before - 1_000_000))
        expected = project_path.stat().st_mtime_ns

        store.upsert_entry(self.entry(title="Second fact"), self.project, self.knowledge_root)

        self.assertEqual(expected, project_path.stat().st_mtime_ns)

    def test_register_workspace_project_captures_current_navigation_metadata(self) -> None:
        (self.project / ".codegraph").mkdir()
        agents = self.project / "AGENTS.md"
        agents.write_text("# Local rules\n", encoding="utf-8")

        result = store.register_workspace_project(
            self.project,
            self.knowledge_root,
            aliases=["demo", "handler service"],
            domains=["requests"],
            purpose="Routes request handling work",
            operator_hints=["Start here for handler failures"],
        )

        payload = json.loads(Path(result["path"]).read_text(encoding="utf-8"))
        self.assertEqual("added", result["action"])
        self.assertEqual(self.identity.key, payload["project_key"])
        self.assertEqual(str(self.project.resolve()), payload["root"])
        self.assertEqual(["demo", "handler service"], payload["aliases"])
        self.assertTrue(payload["codegraph"]["present"])
        self.assertEqual(store.sha256_file(agents), payload["policy"]["sha256"])
        self.assertEqual("filesystem-and-git", payload["metadata_basis"])

    def test_register_workspace_project_refreshes_one_record_without_duplicates(self) -> None:
        first = store.register_workspace_project(
            self.project,
            self.knowledge_root,
            aliases=["demo"],
            domains=["requests"],
            purpose="Initial purpose",
            operator_hints=[],
        )
        second = store.register_workspace_project(
            self.project,
            self.knowledge_root,
            aliases=["demo", "service"],
            domains=["requests"],
            purpose="Updated purpose",
            operator_hints=["Inspect handlers"],
        )

        self.assertEqual(first["path"], second["path"])
        self.assertEqual("refreshed", second["action"])
        project_dir = self.knowledge_root / "_workspace" / "projects"
        self.assertEqual(1, len(list(project_dir.glob("*.json"))))

    def test_same_remote_subdirectories_are_preserved_as_distinct_entry_points(self) -> None:
        nested = self.project / "services" / "media"
        nested.mkdir(parents=True)
        with (
            mock.patch.object(store, "_git_remote", return_value="ssh://git@example.com/acme/demo.git"),
            mock.patch.object(store, "_git_toplevel", return_value=self.project, create=True),
        ):
            first = store.register_workspace_project(
                self.project,
                self.knowledge_root,
                aliases=["demo"],
                domains=["platform"],
                purpose="Repository root",
                operator_hints=[],
            )
            second = store.register_workspace_project(
                nested,
                self.knowledge_root,
                aliases=["media"],
                domains=["streaming"],
                purpose="Media service entry",
                operator_hints=["Use the nested CodeGraph index"],
            )

        payload = json.loads(Path(second["path"]).read_text(encoding="utf-8"))
        self.assertEqual(first["project_key"], second["project_key"])
        self.assertEqual(str(self.project.resolve()), payload["root"])
        self.assertEqual(
            [str(self.project.resolve()), str(nested.resolve())],
            [item["path"] for item in payload["entry_points"]],
        )
        self.assertEqual(["demo", "media"], payload["aliases"])
        self.assertEqual(["platform", "streaming"], payload["domains"])

    def test_workspace_query_finds_projects_and_operator_routes(self) -> None:
        project_result = store.register_workspace_project(
            self.project,
            self.knowledge_root,
            aliases=["demo"],
            domains=["streaming"],
            purpose="Playback service",
            operator_hints=[],
        )
        project_key = project_result["project_key"]
        route = {
            "schema_version": 1,
            "record_type": "workspace-route",
            "title": "Playback investigation",
            "triggers": ["playback", "recording"],
            "project_keys": [project_key],
            "guidance": "Start in the playback service.",
            "basis": "operator-provided",
            "evidence": [],
            "verified_at": "2026-10-23T00:00:00Z",
            "status": "current",
        }
        route_result = store.upsert_workspace_route(route, self.knowledge_root)

        results = store.query_workspace(self.knowledge_root, text="playback")

        self.assertEqual("added", route_result["action"])
        self.assertEqual([project_key], [item["project_key"] for item in results["projects"]])
        self.assertEqual(["Playback investigation"], [item["title"] for item in results["routes"]])

    def test_workspace_route_rejects_unknown_project_keys(self) -> None:
        route = {
            "schema_version": 1,
            "record_type": "workspace-route",
            "title": "Unknown route",
            "triggers": ["unknown"],
            "project_keys": ["missing-project-123"],
            "guidance": "Do not guess.",
            "basis": "operator-provided",
            "evidence": [],
            "verified_at": "2026-10-23T00:00:00Z",
            "status": "current",
        }

        with self.assertRaises(store.ValidationError):
            store.upsert_workspace_route(route, self.knowledge_root)

    def test_code_verified_route_requires_current_evidence_from_each_project(self) -> None:
        registered = store.register_workspace_project(
            self.project,
            self.knowledge_root,
            aliases=["demo"],
            domains=["requests"],
            purpose="Request service",
            operator_hints=[],
        )
        route = {
            "schema_version": 1,
            "record_type": "workspace-route",
            "title": "Unproven dependency",
            "triggers": ["dependency"],
            "project_keys": [registered["project_key"]],
            "guidance": "Claims a technical dependency.",
            "basis": "code-verified",
            "evidence": [],
            "verified_at": "2026-10-23T00:00:00Z",
            "status": "current",
        }

        with self.assertRaises(store.ValidationError):
            store.upsert_workspace_route(route, self.knowledge_root)

    def test_workspace_revalidation_reports_policy_change_without_writing_in_check_only_mode(self) -> None:
        agents = self.project / "AGENTS.md"
        agents.write_text("# Original rules\n", encoding="utf-8")
        registered = store.register_workspace_project(
            self.project,
            self.knowledge_root,
            aliases=["demo"],
            domains=["requests"],
            purpose="Request service",
            operator_hints=[],
        )
        record_path = Path(registered["path"])
        original = record_path.read_bytes()
        agents.write_text("# Changed rules\n", encoding="utf-8")

        result = store.revalidate_workspace(self.knowledge_root, write=False)

        self.assertEqual(original, record_path.read_bytes())
        self.assertEqual(1, result["would_change"])
        self.assertEqual(
            [{"record_type": "workspace-project", "record_id": registered["project_key"], "action": "needs-reverification"}],
            result["maintenance"],
        )

    def test_workspace_revalidation_marks_missing_repository_for_reverification(self) -> None:
        registered = store.register_workspace_project(
            self.project,
            self.knowledge_root,
            aliases=["demo"],
            domains=["requests"],
            purpose="Request service",
            operator_hints=[],
        )
        record_path = Path(registered["path"])
        for child in sorted(self.project.rglob("*"), reverse=True):
            if child.is_file():
                child.unlink()
            elif child.is_dir():
                child.rmdir()
        self.project.rmdir()

        result = store.revalidate_workspace(self.knowledge_root)

        payload = json.loads(record_path.read_text(encoding="utf-8"))
        self.assertEqual("needs-reverification", payload["status"])
        self.assertEqual(1, result["changed"])

    def test_validate_store_includes_workspace_records(self) -> None:
        store.register_workspace_project(
            self.project,
            self.knowledge_root,
            aliases=["demo"],
            domains=["requests"],
            purpose="Request service",
            operator_hints=[],
        )

        counts = store.validate_store(self.knowledge_root)

        self.assertEqual(1, counts["workspace_projects"])
        self.assertEqual(0, counts["workspace_routes"])


if __name__ == "__main__":
    unittest.main()


