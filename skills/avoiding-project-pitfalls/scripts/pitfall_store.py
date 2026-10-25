from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit


SCHEMA_VERSION = 1
GLOBAL_RECORD_TYPE = "cross-project-pitfall"
GLOBAL_CATEGORIES = {"general", "cross-project-development"}
ALLOWED_STATUSES = {"candidate", "verified-history", "obsolete"}
ALLOWED_OBSERVATION_KINDS = {
    "log-observation",
    "reproduction",
    "runtime-observation",
    "test-failure",
}
DOCUMENT_EXTENSIONS = {".adoc", ".asciidoc", ".markdown", ".md", ".org", ".rst", ".txt"}
UTC_TIMESTAMP_PATTERN = re.compile(
    r"\A\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z\Z"
)
SECRET_PATTERN = re.compile(
    r"(?i)(?:api[_-]?key|token|secret|password|credential)\s*[:=]\s*\S+"
    r"|(?:sk|ghp|github_pat)_[A-Za-z0-9_-]{12,}|AKIA[0-9A-Z]{16}"
)
REFERENCE_NOTICE = "Reference only; verify the pitfall against current code before using it."


class ValidationError(ValueError):
    pass


class PathBoundaryError(ValidationError):
    pass


@dataclass(frozen=True)
class ProjectIdentity:
    key: str
    display_name: str
    root: str
    remote: str | None


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return slug[:48] or "project"


def normalize_remote(remote: str) -> str:
    value = remote.strip()
    if not value:
        raise ValidationError("Git remote is empty")
    scp_match = re.fullmatch(r"(?:[^@/]+@)?([^:/]+):(.+)", value)
    if scp_match and "://" not in value:
        host, repo_path = scp_match.groups()
    else:
        parsed = urlsplit(value if "://" in value else f"ssh://{value}")
        host = parsed.hostname or ""
        repo_path = parsed.path
    host = host.casefold().strip()
    repo_path = repo_path.strip("/").replace("\\", "/")
    if repo_path.casefold().endswith(".git"):
        repo_path = repo_path[:-4]
    if not host or not repo_path or ".." in PurePosixPath(repo_path).parts:
        raise ValidationError("Git remote cannot be normalized")
    return f"{host}/{repo_path}"


def _git_remote(root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "config", "--get", "remote.origin.url"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    value = result.stdout.strip()
    return value if result.returncode == 0 and value else None


def resolve_project(root: Path) -> ProjectIdentity:
    resolved = root.expanduser().resolve(strict=True)
    if not resolved.is_dir():
        raise ValidationError("Project root must be a directory")
    remote_value = _git_remote(resolved)
    if remote_value:
        remote = normalize_remote(remote_value)
        basis = f"remote:{remote.casefold()}"
        label = remote.rsplit("/", 1)[-1]
    else:
        remote = None
        basis = f"path:{os.path.normcase(str(resolved))}"
        label = resolved.name
    suffix = hashlib.sha256(basis.encode("utf-8")).hexdigest()[:12]
    return ProjectIdentity(
        key=f"{_slug(label)}-{suffix}",
        display_name=label,
        root=str(resolved),
        remote=remote,
    )


def _is_reparse_point(path: Path) -> bool:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return False
    attributes = getattr(info, "st_file_attributes", 0)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return path.is_symlink() or bool(reparse_flag and attributes & reparse_flag)


def ensure_within(path: Path, root: Path) -> Path:
    root_resolved = root.expanduser().resolve(strict=False)
    candidate = path.expanduser().resolve(strict=False)
    try:
        relative = candidate.relative_to(root_resolved)
    except ValueError as exc:
        raise PathBoundaryError("Path resolves outside the allowed root") from exc
    current = root_resolved
    for part in relative.parts:
        current = current / part
        if current.exists() and _is_reparse_point(current):
            raise PathBoundaryError("Path crosses a symbolic link or reparse point")
    return candidate


def _relative_path(value: str, field: str) -> PurePosixPath:
    normalized = value.replace("\\", "/")
    path = PurePosixPath(normalized)
    if path.is_absolute() or not path.parts or any(part in {".", ".."} for part in path.parts):
        raise PathBoundaryError(f"{field} must be a project-relative path")
    return path


def _validate_utc(value: object, field: str) -> None:
    if not isinstance(value, str) or not UTC_TIMESTAMP_PATTERN.fullmatch(value):
        raise ValidationError(f"{field} must be a UTC ISO-8601 timestamp ending in Z")
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValidationError(f"{field} is not a valid timestamp") from exc


def _contains_secret(payload: dict) -> bool:
    return bool(SECRET_PATTERN.search(json.dumps(payload, ensure_ascii=False, sort_keys=True)))


def _normalized_strings(values: list[str]) -> str:
    return "\0".join(sorted(" ".join(value.casefold().split()) for value in values))


def _entry_id(entry: dict, project_key: str) -> str:
    parts = (
        project_key,
        _normalized_strings(entry.get("trigger_conditions") or []),
        _normalized_strings(entry.get("affected_scope") or []),
    )
    return hashlib.sha256("\0".join(parts).encode("utf-8")).hexdigest()[:20]


def _global_pitfall_id(entry: dict) -> str:
    parts = (
        entry.get("category", ""),
        _normalized_strings(entry.get("trigger_conditions") or []),
        _normalized_strings(entry.get("affected_boundaries") or []),
        _normalized_strings(entry.get("related_projects") or []),
    )
    return hashlib.sha256("\0".join(parts).encode("utf-8")).hexdigest()[:20]


def validate_pitfall(
    entry: dict,
    project_key: str,
    project_root: Path,
    *,
    check_hash: bool = True,
    check_files: bool = True,
    stored: bool = False,
) -> None:
    if not isinstance(entry, dict):
        raise ValidationError("Pitfall must be a JSON object")
    if _contains_secret(entry):
        raise ValidationError("Pitfall contains secret-like content")
    required = {
        "schema_version",
        "title",
        "symptom",
        "trigger_conditions",
        "affected_scope",
        "root_cause",
        "historical_evidence",
        "related_code",
        "validated_resolution",
        "current_reverification",
        "observed_at",
        "status",
    }
    if stored:
        required.update({"entry_id", "project_key"})
    missing = sorted(required - entry.keys())
    if missing:
        raise ValidationError(f"Pitfall is missing required fields: {', '.join(missing)}")
    if entry["schema_version"] != SCHEMA_VERSION:
        raise ValidationError("Unsupported schema_version")
    if entry["status"] not in ALLOWED_STATUSES:
        raise ValidationError("Unsupported status")
    if entry.get("project_key") not in {None, project_key}:
        raise ValidationError("project_key does not match the current project")
    for field in ("title", "symptom"):
        if not isinstance(entry[field], str) or not entry[field].strip():
            raise ValidationError(f"{field} must be a non-empty string")
    for field in ("trigger_conditions", "affected_scope", "current_reverification"):
        values = entry[field]
        if not isinstance(values, list) or not values:
            raise ValidationError(f"{field} must be a non-empty list")
        if any(not isinstance(value, str) or not value.strip() for value in values):
            raise ValidationError(f"{field} values must be non-empty strings")
    _validate_utc(entry["observed_at"], "observed_at")

    project_root = project_root.resolve(strict=True)
    scope_paths: set[str] = set()
    for value in entry["affected_scope"]:
        relative = _relative_path(value, "affected_scope")
        normalized = relative.as_posix()
        scope_paths.add(normalized)
        target = ensure_within(project_root.joinpath(*relative.parts), project_root)
        if check_files and not target.is_file():
            raise ValidationError("affected_scope must reference an existing project file")

    evidence_items = entry["historical_evidence"]
    if not isinstance(evidence_items, list):
        raise ValidationError("historical_evidence must be a list")
    for evidence in evidence_items:
        if not isinstance(evidence, dict):
            raise ValidationError("Historical evidence must be an object")
        if evidence.get("kind") not in ALLOWED_OBSERVATION_KINDS:
            raise ValidationError("Unsupported historical evidence kind")
        if not isinstance(evidence.get("summary"), str) or not evidence["summary"].strip():
            raise ValidationError("Historical evidence summary must be non-empty")
        _validate_utc(evidence.get("observed_at"), "historical_evidence.observed_at")

    code_items = entry["related_code"]
    if not isinstance(code_items, list):
        raise ValidationError("related_code must be a list")
    for code in code_items:
        if not isinstance(code, dict):
            raise ValidationError("related_code values must be objects")
        required_code = {"path", "symbol", "line_start", "line_end", "sha256"}
        missing_code = sorted(required_code - code.keys())
        if missing_code:
            raise ValidationError(f"related_code is missing fields: {', '.join(missing_code)}")
        if not isinstance(code["path"], str):
            raise ValidationError("related_code.path must be a string")
        relative = _relative_path(code["path"], "related_code.path")
        if relative.as_posix() not in scope_paths:
            raise ValidationError("Every related_code path must be included in affected_scope")
        if relative.suffix.casefold() in DOCUMENT_EXTENSIONS:
            raise ValidationError("Documentation cannot be used as related code")
        target = ensure_within(project_root.joinpath(*relative.parts), project_root)
        if not isinstance(code["symbol"], str) or not code["symbol"].strip():
            raise ValidationError("related_code.symbol must be a non-empty string")
        if not isinstance(code["line_start"], int) or not isinstance(code["line_end"], int):
            raise ValidationError("related_code lines must be integers")
        if code["line_start"] < 1 or code["line_end"] < code["line_start"]:
            raise ValidationError("related_code line range is invalid")
        digest = code["sha256"]
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValidationError("related_code sha256 is invalid")
        if not target.is_file():
            if check_files:
                raise ValidationError("related_code file does not exist")
            continue
        if check_files and code["line_end"] > len(target.read_bytes().splitlines()):
            raise ValidationError("related_code line range exceeds the referenced file")
        if check_hash and entry["status"] != "obsolete" and sha256_file(target) != digest:
            raise ValidationError("related_code hash does not match current source")

    if entry["status"] == "verified-history":
        for field in ("root_cause", "validated_resolution"):
            if not isinstance(entry[field], str) or not entry[field].strip():
                raise ValidationError(f"verified-history requires non-empty {field}")
        if not evidence_items:
            raise ValidationError("verified-history requires observed failure or runtime evidence")
        if not code_items:
            raise ValidationError("verified-history requires code-supported root cause evidence")

    expected_id = _entry_id(entry, project_key)
    if stored and entry.get("entry_id") != expected_id:
        raise ValidationError("entry_id is not deterministic for this pitfall")
    if not stored and entry.get("entry_id") not in {None, expected_id}:
        raise ValidationError("entry_id is not deterministic for this pitfall")


def validate_global_pitfall(
    entry: dict,
    project_roots: dict[str, Path],
    *,
    check_hash: bool = True,
    check_files: bool = True,
    stored: bool = False,
) -> None:
    if not isinstance(entry, dict):
        raise ValidationError("Global pitfall must be a JSON object")
    if _contains_secret(entry):
        raise ValidationError("Global pitfall contains secret-like content")
    required = {
        "schema_version",
        "record_type",
        "category",
        "title",
        "symptom",
        "trigger_conditions",
        "affected_boundaries",
        "related_projects",
        "root_cause",
        "historical_evidence",
        "related_code",
        "validated_resolution",
        "current_reverification",
        "applicability",
        "invalidation_conditions",
        "observed_at",
        "status",
    }
    if stored:
        required.add("pitfall_id")
    missing = sorted(required - entry.keys())
    if missing:
        raise ValidationError(f"Global pitfall is missing required fields: {', '.join(missing)}")
    if entry["schema_version"] != SCHEMA_VERSION:
        raise ValidationError("Unsupported schema_version")
    if entry["record_type"] != GLOBAL_RECORD_TYPE:
        raise ValidationError("Unsupported global record_type")
    if entry["category"] not in GLOBAL_CATEGORIES:
        raise ValidationError("Unsupported global pitfall category")
    if entry["status"] not in ALLOWED_STATUSES:
        raise ValidationError("Unsupported status")
    for field in ("title", "symptom", "applicability"):
        if not isinstance(entry[field], str) or not entry[field].strip():
            raise ValidationError(f"{field} must be a non-empty string")
    for field in ("root_cause", "validated_resolution"):
        if not isinstance(entry[field], str):
            raise ValidationError(f"{field} must be a string")
    for field in ("trigger_conditions", "affected_boundaries", "current_reverification", "invalidation_conditions"):
        values = entry[field]
        if not isinstance(values, list) or not values:
            raise ValidationError(f"{field} must be a non-empty list")
        if any(not isinstance(value, str) or not value.strip() for value in values):
            raise ValidationError(f"{field} values must be non-empty strings")
    related_projects = entry["related_projects"]
    if not isinstance(related_projects, list) or not related_projects:
        raise ValidationError("related_projects must be a non-empty list")
    if any(not isinstance(value, str) or not value.strip() for value in related_projects):
        raise ValidationError("related_projects values must be non-empty strings")
    if len(set(related_projects)) != len(related_projects):
        raise ValidationError("related_projects must not contain duplicates")
    if entry["category"] == "cross-project-development" and len(related_projects) < 2:
        raise ValidationError("cross-project-development requires at least two related projects")
    _validate_utc(entry["observed_at"], "observed_at")

    roots = {str(key): Path(value).resolve(strict=True) for key, value in project_roots.items()}
    for project_key, root in roots.items():
        if resolve_project(root).key != project_key:
            raise ValidationError("project_roots key does not match the resolved project")
    code_items = entry["related_code"]
    if not isinstance(code_items, list):
        raise ValidationError("related_code must be a list")
    covered_projects: set[str] = set()
    for code in code_items:
        if not isinstance(code, dict):
            raise ValidationError("related_code values must be objects")
        required_code = {"project_key", "path", "symbol", "line_start", "line_end", "sha256"}
        missing_code = sorted(required_code - code.keys())
        if missing_code:
            raise ValidationError(f"related_code is missing fields: {', '.join(missing_code)}")
        project_key = code["project_key"]
        if project_key not in related_projects:
            raise ValidationError("related_code references an unrelated project")
        if not isinstance(code["path"], str):
            raise ValidationError("related_code.path must be a string")
        relative = _relative_path(code["path"], "related_code.path")
        if relative.suffix.casefold() in DOCUMENT_EXTENSIONS:
            raise ValidationError("Documentation cannot be used as related code")
        if not isinstance(code["symbol"], str) or not code["symbol"].strip():
            raise ValidationError("related_code.symbol must be a non-empty string")
        if not isinstance(code["line_start"], int) or not isinstance(code["line_end"], int):
            raise ValidationError("related_code lines must be integers")
        if code["line_start"] < 1 or code["line_end"] < code["line_start"]:
            raise ValidationError("related_code line range is invalid")
        digest = code["sha256"]
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValidationError("related_code sha256 is invalid")
        if project_key not in roots:
            if check_files:
                raise ValidationError("related_code project root is not provided")
            covered_projects.add(project_key)
            continue
        target = ensure_within(roots[project_key].joinpath(*relative.parts), roots[project_key])
        if not target.is_file():
            if check_files:
                raise ValidationError("related_code file does not exist")
            continue
        if check_files and code["line_end"] > len(target.read_bytes().splitlines()):
            raise ValidationError("related_code line range exceeds the referenced file")
        if check_hash and entry["status"] != "obsolete" and sha256_file(target) != digest:
            raise ValidationError("related_code hash does not match current source")
        covered_projects.add(project_key)

    evidence_items = entry["historical_evidence"]
    if not isinstance(evidence_items, list):
        raise ValidationError("historical_evidence must be a list")
    for evidence in evidence_items:
        if not isinstance(evidence, dict):
            raise ValidationError("Historical evidence must be an object")
        if evidence.get("kind") not in ALLOWED_OBSERVATION_KINDS:
            raise ValidationError("Unsupported historical evidence kind")
        if not isinstance(evidence.get("summary"), str) or not evidence["summary"].strip():
            raise ValidationError("Historical evidence summary must be non-empty")
        _validate_utc(evidence.get("observed_at"), "historical_evidence.observed_at")
    if entry["status"] == "verified-history":
        if not entry["root_cause"].strip() or not entry["validated_resolution"].strip():
            raise ValidationError("verified-history requires non-empty root_cause and validated_resolution")
        if not evidence_items or not code_items:
            raise ValidationError("verified-history requires observed evidence and code anchors")
        if covered_projects != set(related_projects):
            raise ValidationError("verified-history requires code evidence from every related project")
    expected_id = _global_pitfall_id(entry)
    if stored and entry.get("pitfall_id") != expected_id:
        raise ValidationError("pitfall_id is not deterministic for this global pitfall")
    if not stored and entry.get("pitfall_id") not in {None, expected_id}:
        raise ValidationError("pitfall_id is not deterministic for this global pitfall")


def atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    except BaseException:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
        raise


def _global_dir(knowledge_root: Path) -> Path:
    return ensure_within(knowledge_root / "_workspace" / "pitfalls", knowledge_root)


def upsert_global_pitfall(
    entry: dict,
    project_roots: dict[str, Path],
    knowledge_root: Path,
) -> Path:
    payload = dict(entry)
    payload["record_type"] = payload.get("record_type", GLOBAL_RECORD_TYPE)
    payload["pitfall_id"] = _global_pitfall_id(payload)
    payload.setdefault("observed_at", utc_now())
    validate_global_pitfall(payload, project_roots, stored=True)
    root = _global_dir(knowledge_root)
    entry_path = ensure_within(root / f"{payload['pitfall_id']}.json", knowledge_root)
    atomic_write_json(entry_path, payload)
    return entry_path


def query_global_pitfalls(knowledge_root: Path, filters: dict) -> list[dict]:
    root = _global_dir(knowledge_root)
    if not root.is_dir():
        return []
    text_filter = str(filters.get("text", "")).casefold()
    results: list[dict] = []
    for path in sorted(root.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if filters.get("category") and payload.get("category") != filters["category"]:
            continue
        if filters.get("status") and payload.get("status") != filters["status"]:
            continue
        if filters.get("project_key") and filters["project_key"] not in payload.get("related_projects", []):
            continue
        if text_filter and text_filter not in json.dumps(payload, ensure_ascii=False).casefold():
            continue
        result = dict(payload)
        result["reference_notice"] = REFERENCE_NOTICE
        results.append(result)
    return sorted(results, key=lambda item: (item.get("title", ""), item.get("pitfall_id", "")))


def revalidate_global_pitfalls(
    project_roots: dict[str, Path],
    knowledge_root: Path,
    *,
    write: bool = True,
) -> dict[str, object]:
    root = _global_dir(knowledge_root)
    result: dict[str, object] = {
        "checked": 0,
        "changed": 0,
        "would_change": 0,
        "obsolete_pitfalls": [],
        "unverified_projects": [],
    }
    if not root.is_dir():
        return result
    for path in sorted(root.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        validate_global_pitfall(payload, project_roots, check_hash=False, check_files=False, stored=True)
        result["checked"] += 1
        if payload["status"] == "obsolete":
            continue
        missing_projects = sorted(set(payload["related_projects"]) - set(project_roots))
        if missing_projects:
            result["unverified_projects"].extend(missing_projects)
            continue
        valid = True
        for code in payload["related_code"]:
            relative = _relative_path(code["path"], "related_code.path")
            source = ensure_within(
                Path(project_roots[code["project_key"]]).joinpath(*relative.parts),
                Path(project_roots[code["project_key"]]),
            )
            if not source.is_file() or sha256_file(source) != code["sha256"]:
                valid = False
                break
        if not valid:
            result["would_change"] += 1
            result["obsolete_pitfalls"].append(payload["pitfall_id"])
            if write:
                payload["status"] = "obsolete"
                atomic_write_json(path, payload)
                result["changed"] += 1
    result["unverified_projects"] = sorted(set(result["unverified_projects"]))
    return result


def upsert_pitfall(entry: dict, project_root: Path, knowledge_root: Path) -> Path:
    identity = resolve_project(project_root)
    payload = dict(entry)
    payload["project_key"] = identity.key
    payload["entry_id"] = _entry_id(payload, identity.key)
    payload.setdefault("observed_at", utc_now())
    validate_pitfall(payload, identity.key, Path(identity.root), stored=True)

    project_dir = ensure_within(knowledge_root / identity.key, knowledge_root)
    entry_path = ensure_within(project_dir / "entries" / f"{payload['entry_id']}.json", knowledge_root)
    project_path = ensure_within(project_dir / "project.json", knowledge_root)
    project_payload = {"schema_version": SCHEMA_VERSION, **asdict(identity)}
    if project_path.exists():
        existing_project = json.loads(project_path.read_text(encoding="utf-8"))
        if existing_project.get("key") != identity.key or existing_project.get("remote") != identity.remote:
            raise ValidationError("Existing project metadata does not match the current project")
    else:
        atomic_write_json(project_path, project_payload)
    atomic_write_json(entry_path, payload)
    return entry_path


def query_pitfalls(project_key: str, knowledge_root: Path, filters: dict) -> list[dict]:
    project_dir = ensure_within(knowledge_root / project_key, knowledge_root)
    entries_dir = ensure_within(project_dir / "entries", knowledge_root)
    if not entries_dir.is_dir():
        return []
    results: list[dict] = []
    text_filter = str(filters.get("text", "")).casefold()
    for path in sorted(entries_dir.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("project_key") != project_key:
            raise ValidationError("Stored pitfall belongs to another project")
        if filters.get("status") and payload.get("status") != filters["status"]:
            continue
        code_items = payload.get("related_code", [])
        if filters.get("path") and not any(item.get("path") == filters["path"] for item in code_items):
            continue
        if filters.get("symbol") and not any(item.get("symbol") == filters["symbol"] for item in code_items):
            continue
        if text_filter and text_filter not in json.dumps(payload, ensure_ascii=False).casefold():
            continue
        result = dict(payload)
        result["reference_notice"] = REFERENCE_NOTICE
        results.append(result)
    return sorted(results, key=lambda item: (item.get("title", ""), item.get("entry_id", "")))


def revalidate_pitfalls(project_root: Path, knowledge_root: Path, *, write: bool = True) -> dict[str, object]:
    identity = resolve_project(project_root)
    project_dir = ensure_within(knowledge_root / identity.key, knowledge_root)
    entries_dir = ensure_within(project_dir / "entries", knowledge_root)
    result: dict[str, object] = {"checked": 0, "changed": 0, "would_change": 0, "obsolete_entries": []}
    if not entries_dir.is_dir():
        return result
    for path in sorted(entries_dir.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        validate_pitfall(
            payload,
            identity.key,
            Path(identity.root),
            check_hash=False,
            check_files=False,
            stored=True,
        )
        result["checked"] += 1
        if payload["status"] == "obsolete":
            continue
        valid = True
        for code in payload["related_code"]:
            relative = _relative_path(code["path"], "related_code.path")
            source = ensure_within(Path(identity.root).joinpath(*relative.parts), Path(identity.root))
            if not source.is_file() or sha256_file(source) != code["sha256"]:
                valid = False
                break
        if not valid:
            result["would_change"] += 1
            result["obsolete_entries"].append(payload["entry_id"])
            if write:
                payload["status"] = "obsolete"
                atomic_write_json(path, payload)
                result["changed"] += 1
    return result


def validate_store(
    knowledge_root: Path,
    project_root: Path | None = None,
    project_roots: dict[str, Path] | None = None,
) -> dict[str, int]:
    counts = {"projects": 0, "entries": 0, "global_pitfalls": 0}
    project_roots = dict(project_roots or {})
    if project_root is not None:
        identity = resolve_project(project_root)
        project_roots.setdefault(identity.key, project_root)
    expected_key = resolve_project(project_root).key if project_root else None
    if not knowledge_root.is_dir():
        return counts
    for project_dir in sorted(path for path in knowledge_root.iterdir() if path.is_dir()):
        if project_dir.name == "_workspace":
            continue
        ensure_within(project_dir, knowledge_root)
        if expected_key and project_dir.name != expected_key:
            continue
        metadata = json.loads((project_dir / "project.json").read_text(encoding="utf-8"))
        if metadata.get("key") != project_dir.name:
            raise ValidationError("Project metadata key does not match its directory")
        validation_root = Path(metadata.get("root", ""))
        check_files = validation_root.is_dir()
        if project_root is not None and project_dir.name == expected_key:
            validation_root = project_root.resolve(strict=True)
            check_files = True
        elif not check_files:
            validation_root = project_dir
        counts["projects"] += 1
        for entry_path in sorted((project_dir / "entries").glob("*.json")):
            payload = json.loads(entry_path.read_text(encoding="utf-8"))
            validate_pitfall(
                payload,
                project_dir.name,
                validation_root,
                check_hash=project_root is not None and project_dir.name == expected_key,
                check_files=check_files,
                stored=True,
            )
            counts["entries"] += 1
    global_dir = _global_dir(knowledge_root)
    if global_dir.is_dir():
        for entry_path in sorted(global_dir.glob("*.json")):
            payload = json.loads(entry_path.read_text(encoding="utf-8"))
            related_keys = set(payload.get("related_projects", []))
            entry_roots = {key: value for key, value in project_roots.items() if key in related_keys}
            complete_roots = related_keys.issubset(entry_roots)
            validate_global_pitfall(
                payload,
                entry_roots,
                check_hash=complete_roots,
                check_files=complete_roots,
                stored=True,
            )
            counts["global_pitfalls"] += 1
    return counts


def load_candidate(source: str, stdin=None) -> dict:
    if source == "-":
        handle = stdin if stdin is not None else sys.stdin
        text = handle.read()
    else:
        text = Path(source).read_text(encoding="utf-8")
    payload = json.loads(text)
    if not isinstance(payload, dict):
        raise ValidationError("Candidate must be a JSON object")
    return payload


def _default_knowledge_root() -> Path:
    return Path(__file__).resolve().parents[1] / "knowledge" / "projects"


def _resolve_project_roots(paths: list[Path]) -> dict[str, Path]:
    roots: dict[str, Path] = {}
    for path in paths:
        identity = resolve_project(path)
        existing = roots.get(identity.key)
        if existing is not None and existing.resolve() != Path(identity.root):
            raise ValidationError("The same project key resolves to multiple project roots")
        roots[identity.key] = Path(identity.root)
    return roots


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Maintain project pitfalls as reference-only knowledge.")
    parser.add_argument("--knowledge-root", type=Path, default=_default_knowledge_root())
    subparsers = parser.add_subparsers(dest="command", required=True)
    resolve = subparsers.add_parser("resolve-project")
    resolve.add_argument("--project-root", required=True, type=Path)
    query = subparsers.add_parser("query")
    query.add_argument("--project-root", required=True, type=Path)
    query.add_argument("--text")
    query.add_argument("--path")
    query.add_argument("--symbol")
    query.add_argument("--status")
    upsert = subparsers.add_parser("upsert")
    upsert.add_argument("--project-root", required=True, type=Path)
    upsert.add_argument("--candidate", required=True, help="JSON file path, or - for stdin")
    revalidate = subparsers.add_parser("revalidate")
    revalidate.add_argument("--project-root", required=True, type=Path)
    revalidate.add_argument(
        "--check-only",
        action="store_true",
        help="Report obsolete entries without modifying stored knowledge",
    )
    validate = subparsers.add_parser("validate")
    validate.add_argument("--project-root", action="append", type=Path)
    global_query = subparsers.add_parser("global-query")
    global_query.add_argument("--text")
    global_query.add_argument("--category")
    global_query.add_argument("--project-key")
    global_query.add_argument("--status")
    global_upsert = subparsers.add_parser("global-upsert")
    global_upsert.add_argument("--project-root", action="append", required=True, type=Path)
    global_upsert.add_argument("--candidate", required=True, help="JSON file path, or - for stdin")
    global_revalidate = subparsers.add_parser("global-revalidate")
    global_revalidate.add_argument("--project-root", action="append", required=True, type=Path)
    global_revalidate.add_argument(
        "--check-only",
        action="store_true",
        help="Report obsolete records without modifying stored knowledge",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "resolve-project":
            output = asdict(resolve_project(args.project_root))
        elif args.command == "query":
            identity = resolve_project(args.project_root)
            filters = {name: getattr(args, name) for name in ("text", "path", "symbol", "status")}
            output = query_pitfalls(identity.key, args.knowledge_root, filters)
        elif args.command == "upsert":
            candidate = load_candidate(args.candidate)
            output = {"path": str(upsert_pitfall(candidate, args.project_root, args.knowledge_root))}
        elif args.command == "revalidate":
            output = revalidate_pitfalls(args.project_root, args.knowledge_root, write=not args.check_only)
        elif args.command == "global-query":
            filters = {name: getattr(args, name) for name in ("text", "category", "project_key", "status")}
            output = query_global_pitfalls(args.knowledge_root, filters)
        elif args.command == "global-upsert":
            candidate = load_candidate(args.candidate)
            roots = _resolve_project_roots(args.project_root)
            output = {"path": str(upsert_global_pitfall(candidate, roots, args.knowledge_root))}
        elif args.command == "global-revalidate":
            roots = _resolve_project_roots(args.project_root)
            output = revalidate_global_pitfalls(roots, args.knowledge_root, write=not args.check_only)
        else:
            paths = args.project_root or []
            roots = _resolve_project_roots(paths)
            output = validate_store(
                args.knowledge_root,
                paths[0] if len(paths) == 1 else None,
                project_roots=roots,
            )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())


