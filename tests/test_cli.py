from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from gpe import __version__
from gpe.repository import EXPECTED_SKILLS, RepositoryError, install_skills, validate_repository


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


class VersionTests(unittest.TestCase):
    def test_version_is_semver_like(self) -> None:
        parts = __version__.split(".")
        self.assertEqual(len(parts), 3)
        self.assertTrue(all(part.isdigit() for part in parts))


if __name__ == "__main__":
    unittest.main()
