from __future__ import annotations

import copy
import io
import json
import tempfile
import unittest
from pathlib import Path

try:
    import pitfall_store as store
except ModuleNotFoundError as exc:
    store = None
    IMPORT_ERROR = exc
else:
    IMPORT_ERROR = None


class PitfallStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertIsNone(IMPORT_ERROR, f"pitfall_store implementation missing: {IMPORT_ERROR}")
        self.temp = tempfile.TemporaryDirectory(prefix="codex-project-pitfalls-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.project = self.base / "project"
        self.knowledge_root = self.base / "knowledge" / "projects"
        source = self.project / "src" / "order_consumer.py"
        source.parent.mkdir(parents=True)
        source.write_text(
            "def handle(command):\n"
            "    if not idempotency.try_acquire(command.key):\n"
            "        return\n"
            "    create_order(command)\n",
            encoding="utf-8",
        )
        self.source = source
        self.identity = store.resolve_project(self.project) if store else None

    def pitfall(self, *, status: str = "verified-history", title: str = "Duplicate order") -> dict:
        return {
            "schema_version": 1,
            "title": title,
            "symptom": "Concurrent delivery created two orders for one business key",
            "trigger_conditions": ["two deliveries share one business key"],
            "affected_scope": ["src/order_consumer.py"],
            "root_cause": "Order creation previously ignored a failed idempotency acquisition",
            "historical_evidence": [
                {
                    "kind": "test-failure",
                    "summary": "Concurrency regression test observed two created orders",
                    "observed_at": "2026-10-23T00:00:00Z",
                }
            ],
            "related_code": [
                {
                    "path": "src/order_consumer.py",
                    "symbol": "handle",
                    "line_start": 1,
                    "line_end": 4,
                    "sha256": store.sha256_file(self.source),
                }
            ],
            "validated_resolution": "Return when the atomic idempotency acquisition fails",
            "current_reverification": [
                "Inspect OrderConsumer.handle and IdempotencyStore.tryAcquire",
                "Run the concurrent duplicate-delivery regression test",
            ],
            "observed_at": "2026-10-23T00:00:00Z",
            "status": status,
        }

    def test_verified_history_requires_observation_and_code_root_cause(self) -> None:
        for field, value in (
            ("historical_evidence", []),
            ("root_cause", ""),
            ("related_code", []),
        ):
            entry = self.pitfall()
            entry[field] = value
            with self.subTest(field=field):
                with self.assertRaises(store.ValidationError):
                    store.validate_pitfall(entry, self.identity.key, self.project)

    def test_candidate_cannot_be_presented_as_current_fact(self) -> None:
        store.upsert_pitfall(self.pitfall(status="candidate"), self.project, self.knowledge_root)
        results = store.query_pitfalls(self.identity.key, self.knowledge_root, {"status": "candidate"})
        self.assertEqual(1, len(results))
        self.assertEqual("candidate", results[0]["status"])
        self.assertIn("reference", results[0]["reference_notice"].casefold())
        self.assertNotIn("current_fact", results[0])

    def test_reverification_instructions_are_required(self) -> None:
        entry = self.pitfall()
        entry["current_reverification"] = []
        with self.assertRaises(store.ValidationError):
            store.validate_pitfall(entry, self.identity.key, self.project)

    def test_related_code_cannot_escape_project_root(self) -> None:
        outside = self.base / "outside.py"
        outside.write_text("do_not_change = True\n", encoding="utf-8")
        original = outside.read_bytes()
        entry = self.pitfall()
        entry["related_code"][0]["path"] = "../outside.py"
        with self.assertRaises(store.PathBoundaryError):
            store.upsert_pitfall(entry, self.project, self.knowledge_root)
        self.assertEqual(original, outside.read_bytes())

    def test_upsert_merges_same_project_trigger_and_scope(self) -> None:
        first = store.upsert_pitfall(self.pitfall(), self.project, self.knowledge_root)
        updated = self.pitfall(title="Duplicate delivery creates duplicate order")
        updated["validated_resolution"] = "Guard order creation with the acquisition result and a unique key"
        second = store.upsert_pitfall(updated, self.project, self.knowledge_root)
        self.assertEqual(first, second)
        self.assertEqual(1, len(list(first.parent.glob("*.json"))))

    def test_different_projects_never_merge(self) -> None:
        other_project = self.base / "other-project"
        other_source = other_project / "src" / "order_consumer.py"
        other_source.parent.mkdir(parents=True)
        other_source.write_text(self.source.read_text(encoding="utf-8"), encoding="utf-8")
        first = store.upsert_pitfall(self.pitfall(), self.project, self.knowledge_root)
        other = self.pitfall()
        other["related_code"][0]["sha256"] = store.sha256_file(other_source)
        second = store.upsert_pitfall(other, other_project, self.knowledge_root)
        self.assertNotEqual(first, second)
        self.assertNotEqual(
            json.loads(first.read_text(encoding="utf-8"))["project_key"],
            json.loads(second.read_text(encoding="utf-8"))["project_key"],
        )

    def test_obsolete_preserves_record_instead_of_deleting(self) -> None:
        path = store.upsert_pitfall(self.pitfall(), self.project, self.knowledge_root)
        self.source.write_text("def handle(command):\n    create_order(command)\n", encoding="utf-8")
        result = store.revalidate_pitfalls(self.project, self.knowledge_root)
        self.assertTrue(path.is_file())
        self.assertEqual("obsolete", json.loads(path.read_text(encoding="utf-8"))["status"])
        self.assertEqual(1, result["changed"])

    def test_query_returns_reference_language_and_reverification(self) -> None:
        store.upsert_pitfall(self.pitfall(), self.project, self.knowledge_root)
        result = store.query_pitfalls(
            self.identity.key,
            self.knowledge_root,
            {"path": "src/order_consumer.py", "symbol": "handle"},
        )[0]
        self.assertIn("reference", result["reference_notice"].casefold())
        self.assertEqual(self.pitfall()["current_reverification"], result["current_reverification"])

    def test_atomic_write_preserves_previous_file_on_failure(self) -> None:
        path = store.upsert_pitfall(self.pitfall(), self.project, self.knowledge_root)
        original = path.read_bytes()
        invalid = copy.deepcopy(self.pitfall())
        invalid["related_code"][0]["sha256"] = "0" * 64
        with self.assertRaises(store.ValidationError):
            store.upsert_pitfall(invalid, self.project, self.knowledge_root)
        self.assertEqual(original, path.read_bytes())
        self.assertEqual([], list(path.parent.glob("*.tmp")))

    def test_secret_like_values_are_rejected(self) -> None:
        entry = self.pitfall()
        secret = "ghp_" + ("x" * 24)
        entry["historical_evidence"][0]["summary"] = f"token={secret}"
        with self.assertRaises(store.ValidationError) as caught:
            store.upsert_pitfall(entry, self.project, self.knowledge_root)
        self.assertNotIn(secret, str(caught.exception))

    def test_remote_identity_ignores_credentials_and_dot_git(self) -> None:
        left = store.normalize_remote("https://user:token@example.com/acme/demo.git")
        right = store.normalize_remote("git@example.com:acme/demo.git")
        self.assertEqual("example.com/acme/demo", left)
        self.assertEqual(left, right)

    def test_candidate_can_be_loaded_from_stdin_without_staging_file(self) -> None:
        candidate = self.pitfall(status="candidate")
        loaded = store.load_candidate("-", io.StringIO(json.dumps(candidate)))
        self.assertEqual(candidate, loaded)
        self.assertEqual([], list(self.knowledge_root.rglob("*")))

    def _global_pitfall(self, other_project: Path, *, status: str = "verified-history") -> tuple[dict, dict[str, Path]]:
        other_source = other_project / "src" / "publisher.py"
        other_source.parent.mkdir(parents=True)
        other_source.write_text(
            "def publish(event):\n"
            "    return transport.send(event)\n",
            encoding="utf-8",
        )
        other_identity = store.resolve_project(other_project)
        candidate = {
            "schema_version": 1,
            "record_type": "cross-project-pitfall",
            "category": "cross-project-development",
            "title": "Producer and consumer protocol drift",
            "symptom": "The consumer rejects messages after a producer deployment",
            "trigger_conditions": ["producer and consumer deploy independently"],
            "affected_boundaries": ["event payload contract", "producer-consumer deployment boundary"],
            "related_projects": [self.identity.key, other_identity.key],
            "root_cause": "The producer changed a required field without a compatibility window",
            "historical_evidence": [
                {
                    "kind": "runtime-observation",
                    "summary": "Mixed-version deployment rejected newly published events",
                    "observed_at": "2026-10-23T00:00:00Z",
                }
            ],
            "related_code": [
                {
                    "project_key": self.identity.key,
                    "path": "src/order_consumer.py",
                    "symbol": "handle",
                    "line_start": 1,
                    "line_end": 4,
                    "sha256": store.sha256_file(self.source),
                },
                {
                    "project_key": other_identity.key,
                    "path": "src/publisher.py",
                    "symbol": "publish",
                    "line_start": 1,
                    "line_end": 2,
                    "sha256": store.sha256_file(other_source),
                },
            ],
            "validated_resolution": "Deploy a backward-compatible producer before switching the consumer",
            "current_reverification": [
                "Inspect both producer and consumer contract handling",
                "Run the mixed-version compatibility test",
            ],
            "applicability": "Only when producer and consumer are independently deployed",
            "invalidation_conditions": ["The contract is versioned and compatibility is enforced in code"],
            "observed_at": "2026-10-23T00:00:00Z",
            "status": status,
        }
        roots = {self.identity.key: self.project, other_identity.key: other_project}
        return candidate, roots

    def test_cross_project_record_requires_code_from_each_related_project(self) -> None:
        other_project = self.base / "publisher-project"
        candidate, roots = self._global_pitfall(other_project)
        path = store.upsert_global_pitfall(candidate, roots, self.knowledge_root)
        self.assertTrue(path.is_file())
        stored = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual("cross-project-development", stored["category"])
        self.assertEqual(2, len(stored["related_projects"]))

    def test_cross_project_record_rejects_missing_project_evidence(self) -> None:
        other_project = self.base / "publisher-project"
        candidate, roots = self._global_pitfall(other_project)
        candidate["related_code"] = [candidate["related_code"][0]]
        with self.assertRaises(store.ValidationError):
            store.upsert_global_pitfall(candidate, roots, self.knowledge_root)

    def test_global_related_code_cannot_escape_project_root(self) -> None:
        other_project = self.base / "publisher-project"
        candidate, roots = self._global_pitfall(other_project)
        candidate["related_code"][1]["path"] = "../outside.py"
        with self.assertRaises(store.PathBoundaryError):
            store.upsert_global_pitfall(candidate, roots, self.knowledge_root)

    def test_global_query_is_reference_only_and_revalidation_obsoletes_changed_code(self) -> None:
        other_project = self.base / "publisher-project"
        candidate, roots = self._global_pitfall(other_project)
        store.upsert_global_pitfall(candidate, roots, self.knowledge_root)
        results = store.query_global_pitfalls(
            self.knowledge_root,
            {"category": "cross-project-development", "project_key": self.identity.key},
        )
        self.assertEqual(1, len(results))
        self.assertIn("reference", results[0]["reference_notice"].casefold())
        (other_project / "src" / "publisher.py").write_text("def publish(event):\n    return None\n", encoding="utf-8")
        result = store.revalidate_global_pitfalls(roots, self.knowledge_root)
        self.assertEqual(1, result["changed"])
        self.assertEqual("obsolete", json.loads(next(self.knowledge_root.joinpath("_workspace", "pitfalls").glob("*.json")).read_text(encoding="utf-8"))["status"])

    def test_general_record_is_allowed_with_one_project_but_cross_project_is_not(self) -> None:
        candidate, roots = self._global_pitfall(self.base / "publisher-project", status="candidate")
        candidate["category"] = "general"
        candidate["related_projects"] = [self.identity.key]
        candidate["related_code"] = [candidate["related_code"][0]]
        store.upsert_global_pitfall(candidate, {self.identity.key: self.project}, self.knowledge_root)
        candidate["category"] = "cross-project-development"
        with self.assertRaises(store.ValidationError):
            store.upsert_global_pitfall(candidate, {self.identity.key: self.project}, self.knowledge_root)


if __name__ == "__main__":
    unittest.main()


