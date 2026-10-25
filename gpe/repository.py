from __future__ import annotations

import re
import shutil
from pathlib import Path


EXPECTED_SKILLS = (
    "ai-necessity-audit",
    "avoiding-project-pitfalls",
    "confirm-before-work",
    "evidence-discipline",
    "grounding-project-knowledge",
    "manual-e2e-test-handbook",
)

RUNTIME_DIRECTORIES = {
    "knowledge",
    "workspace",
    "runs",
    "evidence",
    "logs",
}


class RepositoryError(ValueError):
    """Raised when a repository or installation request is unsafe or invalid."""


def find_repo_root(source: Path | None = None) -> Path:
    candidate = (source or Path.cwd()).expanduser().resolve()
    if candidate.is_file():
        candidate = candidate.parent
    if not (candidate / "skills").is_dir():
        raise RepositoryError(f"Not a skill-suite repository: {candidate}")
    return candidate


def discover_skill_names(root: Path) -> tuple[str, ...]:
    return tuple(
        sorted(
            path.name
            for path in (root / "skills").iterdir()
            if path.is_dir() and (path / "SKILL.md").is_file()
        )
    )


def _frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---", 4)
    if end < 0:
        return {}
    values: dict[str, str] = {}
    for line in text[4:end].splitlines():
        match = re.match(r"^([A-Za-z][A-Za-z0-9_-]*):\s*(.*)$", line)
        if match:
            values[match.group(1)] = match.group(2).strip().strip('"')
    return values


def validate_repository(root: Path) -> list[str]:
    root = root.expanduser().resolve()
    errors: list[str] = []
    actual = discover_skill_names(root) if (root / "skills").is_dir() else ()
    if actual != EXPECTED_SKILLS:
        errors.append(f"skills mismatch: expected {EXPECTED_SKILLS}, found {actual}")

    for skill_name in EXPECTED_SKILLS:
        skill_root = root / "skills" / skill_name
        skill_file = skill_root / "SKILL.md"
        agent_file = skill_root / "agents" / "openai.yaml"
        if not skill_file.is_file():
            errors.append(f"missing {skill_file.relative_to(root)}")
            continue
        metadata = _frontmatter(skill_file.read_text(encoding="utf-8"))
        if metadata.get("name") != skill_name:
            errors.append(f"{skill_file.relative_to(root)} has name {metadata.get('name')!r}")
        if not metadata.get("description"):
            errors.append(f"{skill_file.relative_to(root)} is missing description")
        if skill_name == "manual-e2e-test-handbook":
            skill_text = skill_file.read_text(encoding="utf-8")
            for marker in ("operating system", "cmd.exe", "POSIX", "target-specific"):
                if marker not in skill_text:
                    errors.append(f"{skill_file.relative_to(root)} is missing platform marker {marker!r}")
        if not agent_file.is_file():
            errors.append(f"missing {agent_file.relative_to(root)}")
        else:
            agent_text = agent_file.read_text(encoding="utf-8")
            for marker in ("interface:", "display_name:", "short_description:"):
                if marker not in agent_text:
                    errors.append(f"{agent_file.relative_to(root)} is missing {marker}")

    for required in (
        root / "README.md",
        root / "LICENSE",
        root / "docs" / "installation.md",
        root / "docs" / "workflow.md",
        root / "pyproject.toml",
    ):
        if not required.is_file():
            errors.append(f"missing {required.relative_to(root)}")

    gitignore = root / ".gitignore"
    if not gitignore.is_file():
        errors.append("missing .gitignore")
    else:
        gitignore_text = gitignore.read_text(encoding="utf-8")
        for marker in ("skills/*/knowledge/", "skills/*/workspace/"):
            if marker not in gitignore_text:
                errors.append(f".gitignore is missing {marker}")
    return errors


def _ensure_safe_target(source: Path, target: Path) -> None:
    if target == source or source in target.parents:
        raise RepositoryError("Installation target must not be the source repository or its child")
    if target.exists() and target.is_symlink():
        raise RepositoryError("Installation target must not be a symbolic link")


def install_skills(
    source: Path,
    target: Path,
    *,
    skills: tuple[str, ...] | None = None,
    force: bool = False,
) -> list[Path]:
    source_root = find_repo_root(source)
    errors = validate_repository(source_root)
    if errors:
        raise RepositoryError("Repository validation failed: " + "; ".join(errors))
    target_root = target.expanduser().resolve()
    _ensure_safe_target(source_root, target_root)
    selected = tuple(skills or EXPECTED_SKILLS)
    unknown = sorted(set(selected) - set(EXPECTED_SKILLS))
    if unknown:
        raise RepositoryError(f"Unknown skills: {', '.join(unknown)}")

    installed: list[Path] = []
    target_root.mkdir(parents=True, exist_ok=True)
    ignore = shutil.ignore_patterns(*RUNTIME_DIRECTORIES)
    for skill_name in selected:
        source_skill = source_root / "skills" / skill_name
        destination = target_root / skill_name
        if destination.exists() and not force:
            raise RepositoryError(f"Destination already exists: {destination}")
        if destination.is_symlink():
            raise RepositoryError(f"Destination must not be a symbolic link: {destination}")
        shutil.copytree(source_skill, destination, dirs_exist_ok=force, ignore=ignore)
        installed.append(destination)
    return installed
