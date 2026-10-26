from __future__ import annotations

import re
import shutil
import tempfile
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


def _skills_directory(root: Path) -> Path:
    for name in ("skills", "_skills"):
        candidate = root / name
        if candidate.is_dir():
            return candidate
    raise RepositoryError(f"Not a skill-suite repository or packaged distribution: {root}")


def find_repo_root(source: Path | None = None) -> Path:
    if source is None:
        candidate = Path.cwd().expanduser().resolve()
        if not (candidate / "skills").is_dir():
            packaged = Path(__file__).resolve().parent
            if (packaged / "_skills").is_dir():
                return packaged
    else:
        candidate = source.expanduser().resolve()
    if candidate.is_file():
        candidate = candidate.parent
    if not (candidate / "skills").is_dir() and not (candidate / "_skills").is_dir():
        raise RepositoryError(f"Not a skill-suite repository: {candidate}")
    return candidate


def discover_skill_names(root: Path) -> tuple[str, ...]:
    return tuple(
        sorted(
            path.name
            for path in _skills_directory(root).iterdir()
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


def _fallback_yaml_mapping(text: str) -> dict[str, object]:
    """Validate the small mapping-only manifest format when PyYAML is absent."""
    result: dict[str, object] = {}
    stack: list[tuple[int, dict[str, object]]] = [(-1, result)]
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        if "\t" in raw_line:
            raise ValueError(f"line {line_number}: tabs are not valid YAML indentation")
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        content = raw_line.strip()
        if ":" not in content:
            raise ValueError(f"line {line_number}: expected a mapping entry")
        key, value = content.split(":", 1)
        key = key.strip()
        value = value.strip()
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", key):
            raise ValueError(f"line {line_number}: invalid mapping key")
        while stack[-1][0] >= indent:
            stack.pop()
        mapping = stack[-1][1]
        if key in mapping:
            raise ValueError(f"line {line_number}: duplicate mapping key {key!r}")
        if value:
            if value[0] in "[{(" or value[-1:] in "]})":
                pairs = {"[": "]", "{": "}", "(": ")"}
                if value[0] in pairs and value[-1:] != pairs[value[0]]:
                    raise ValueError(f"line {line_number}: unbalanced value delimiters")
            if value.startswith(('"', "'")) and (len(value) < 2 or value[-1] != value[0]):
                raise ValueError(f"line {line_number}: unterminated quoted value")
            if value.lower() == "true":
                mapping[key] = True
            elif value.lower() == "false":
                mapping[key] = False
            elif value.startswith(('"', "'")) and value[-1] == value[0]:
                mapping[key] = value[1:-1]
            else:
                mapping[key] = value
        else:
            child: dict[str, object] = {}
            mapping[key] = child
            stack.append((indent, child))
    return result


def validate_agent_manifest(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"{path}: cannot read manifest: {exc}"]
    try:
        try:
            import yaml  # type: ignore[import-not-found]
        except ModuleNotFoundError:
            document = _fallback_yaml_mapping(text)
        else:
            document = yaml.safe_load(text)
    except Exception as exc:  # parser-specific exception types vary by backend
        return [f"{path}: invalid YAML: {exc}"]
    if not isinstance(document, dict):
        return [f"{path}: YAML root must be a mapping"]
    interface = document.get("interface")
    if not isinstance(interface, dict):
        errors.append(f"{path}: interface must be a mapping")
    else:
        for key in ("display_name", "short_description"):
            if not isinstance(interface.get(key), str) or not interface[key].strip():
                errors.append(f"{path}: interface.{key} must be a non-empty string")
        if "default_prompt" in interface and (
            not isinstance(interface.get("default_prompt"), str) or not interface["default_prompt"].strip()
        ):
            errors.append(f"{path}: interface.default_prompt must be a non-empty string")
    policy = document.get("policy")
    if policy is not None and (
        not isinstance(policy, dict) or not isinstance(policy.get("allow_implicit_invocation"), bool)
    ):
        errors.append(f"{path}: policy.allow_implicit_invocation must be a boolean")
    return errors


def validate_repository(root: Path) -> list[str]:
    root = root.expanduser().resolve()
    errors: list[str] = []
    packaged = (root / "_skills").is_dir() and not (root / "skills").is_dir()
    skills_dir = root / "_skills" if packaged else root / "skills"
    actual = discover_skill_names(root) if skills_dir.is_dir() else ()
    if actual != EXPECTED_SKILLS:
        errors.append(f"skills mismatch: expected {EXPECTED_SKILLS}, found {actual}")

    for skill_name in EXPECTED_SKILLS:
        skill_root = skills_dir / skill_name
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
            errors.extend(validate_agent_manifest(agent_file))

    if not packaged:
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
    source: Path | None,
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
    destinations = {skill_name: target_root / skill_name for skill_name in selected}
    for skill_name, destination in destinations.items():
        if destination.is_symlink():
            raise RepositoryError(f"Destination must not be a symbolic link: {destination}")
        if destination.exists() and not force:
            raise RepositoryError(f"Destination already exists: {destination}")
        if destination.exists() and not destination.is_dir():
            raise RepositoryError(f"Destination must be a directory: {destination}")

    staging_root = Path(tempfile.mkdtemp(prefix=".gpe-install-", dir=target_root))
    backups: dict[Path, Path] = {}
    try:
        for skill_name, destination in destinations.items():
            source_skill = _skills_directory(source_root) / skill_name
            staged = staging_root / skill_name
            shutil.copytree(source_skill, staged, ignore=ignore)
            if force and destination.is_dir():
                for runtime_name in RUNTIME_DIRECTORIES:
                    runtime_source = destination / runtime_name
                    if runtime_source.is_symlink():
                        raise RepositoryError(f"Runtime directory must not be a symbolic link: {runtime_source}")
                    if runtime_source.is_dir():
                        shutil.copytree(runtime_source, staged / runtime_name)

        for skill_name, destination in destinations.items():
            staged = staging_root / skill_name
            if destination.exists():
                backup = target_root / f".{skill_name}.gpe-backup"
                if backup.exists():
                    shutil.rmtree(backup)
                destination.replace(backup)
                backups[destination] = backup
            staged.replace(destination)
            installed.append(destination)
    except Exception as exc:
        for destination in installed:
            if destination.is_dir() and not destination.is_symlink():
                shutil.rmtree(destination)
        for destination, backup in backups.items():
            if backup.exists() and not destination.exists():
                backup.replace(destination)
        if isinstance(exc, RepositoryError):
            raise
        raise RepositoryError(f"Installation failed and was rolled back: {exc}") from exc
    finally:
        if staging_root.exists():
            shutil.rmtree(staging_root)
        for backup in backups.values():
            if backup.exists():
                shutil.rmtree(backup)
    return installed
