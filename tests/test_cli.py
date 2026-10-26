from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from gpe import __version__
from gpe.cli import _test_commands
from gpe.repository import (
    EXPECTED_SKILLS,
    RepositoryError,
    install_skills,
    validate_agent_manifest,
    validate_repository,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


class RepositoryValidationTests(unittest.TestCase):
    def test_current_repository_has_a_complete_skill_manifest(self) -> None:
        self.assertEqual(validate_repository(REPOSITORY_ROOT), [])

    def test_all_expected_skills_are_declared(self) -> None:
        self.assertEqual(
            tuple(
                sorted(skill.name for skill in (REPOSITORY_ROOT / "skills").iterdir() if skill.is_dir())
            ),
            EXPECTED_SKILLS,
        )

    def test_e2e_skill_declares_platform_specific_command_rules(self) -> None:
        skill_text = (REPOSITORY_ROOT / "skills" / "manual-e2e-test-handbook" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        for marker in ("operating system", "cmd.exe", "POSIX", "target-specific"):
            self.assertIn(marker, skill_text)

    def test_invalid_agent_yaml_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = Path(temp_dir) / "openai.yaml"
            manifest.write_text("interface:\n  display_name: [unterminated\n", encoding="utf-8")

            errors = validate_agent_manifest(manifest)

            self.assertTrue(errors)
            self.assertIn("YAML", errors[0])

    def test_test_commands_use_absolute_paths(self) -> None:
        for command in _test_commands(REPOSITORY_ROOT):
            for option in ("-s", "--cases"):
                if option in command:
                    argument = command[command.index(option) + 1]
                    self.assertTrue(Path(argument).is_absolute(), command)


class InstallerTests(unittest.TestCase):
    def test_install_copies_selected_skill_without_runtime_directories(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "skill-root"
            installed = install_skills(
                REPOSITORY_ROOT,
                target,
                skills=("ai-necessity-audit",),
            )

            self.assertEqual(installed, [target / "ai-necessity-audit"])
            self.assertTrue((target / "ai-necessity-audit" / "SKILL.md").is_file())
            self.assertTrue((target / "ai-necessity-audit" / "agents" / "openai.yaml").is_file())
            self.assertFalse((target / "ai-necessity-audit" / "workspace").exists())
            self.assertFalse((target / "ai-necessity-audit" / "knowledge").exists())

    def test_existing_destination_requires_force(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "skill-root"
            destination = target / "ai-necessity-audit"
            destination.mkdir(parents=True)

            with self.assertRaises(RepositoryError):
                install_skills(
                    REPOSITORY_ROOT,
                    target,
                    skills=("ai-necessity-audit",),
                )

    def test_force_removes_stale_static_files_but_preserves_runtime_data(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "skill-root"
            destination = target / "ai-necessity-audit"
            destination.mkdir(parents=True)
            (destination / "obsolete.md").write_text("stale", encoding="utf-8")
            (destination / "workspace").mkdir()
            (destination / "workspace" / "run.json").write_text("runtime", encoding="utf-8")

            install_skills(REPOSITORY_ROOT, target, skills=("ai-necessity-audit",), force=True)

            self.assertFalse((destination / "obsolete.md").exists())
            self.assertEqual("runtime", (destination / "workspace" / "run.json").read_text(encoding="utf-8"))

    def test_force_preflights_all_destinations_before_replacing_any(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "skill-root"
            blocked = target / "avoiding-project-pitfalls"
            blocked.parent.mkdir(parents=True)
            blocked.write_text("not a directory", encoding="utf-8")

            with self.assertRaises(RepositoryError):
                install_skills(
                    REPOSITORY_ROOT,
                    target,
                    skills=("ai-necessity-audit", "avoiding-project-pitfalls"),
                    force=True,
                )

            self.assertFalse((target / "ai-necessity-audit").exists())


class VersionTests(unittest.TestCase):
    def test_version_is_semver_like(self) -> None:
        parts = __version__.split(".")
        self.assertEqual(len(parts), 3)
        self.assertTrue(all(part.isdigit() for part in parts))


if __name__ == "__main__":
    unittest.main()
