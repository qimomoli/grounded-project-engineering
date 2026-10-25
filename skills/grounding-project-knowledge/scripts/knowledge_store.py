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
ALLOWED_STATUSES = {"current", "needs-reverification", "retired"}
ALLOWED_ENTRY_KINDS = {
    "build",
    "call-flow",
    "configuration",
    "data-model",
    "dependency",
    "error-handling",
    "interface",
    "module-role",
    "security-boundary",
    "state-transition",
}
ALLOWED_EVIDENCE_KINDS = {
    "source",
    "runtime-config",
    "build-definition",
    "migration",
    "interface-definition",
}
ALLOWED_ROUTE_BASES = {"operator-provided", "code-verified"}
WORKSPACE_DIR_NAME = "_workspace"
DOCUMENT_EXTENSIONS = {".adoc", ".asciidoc", ".markdown", ".md", ".org", ".rst", ".txt"}
UTC_TIMESTAMP_PATTERN = re.compile(
    r"\A\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z\Z"
)
SECRET_PATTERN = re.compile(
    r"(?i)(?:api[_-]?key|token|secret|password|credential)\s*[:=]\s*\S+"
    r"|(?:sk|ghp|github_pat)_[A-Za-z0-9_-]{12,}|AKIA[0-9A-Z]{16}"
)


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


def _git_toplevel(root: Path) -> Path | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    value = result.stdout.strip()
    if result.returncode != 0 or not value:
        return None
    candidate = Path(value).resolve(strict=True)
    return candidate if candidate.is_dir() else None


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
        normalized_path = os.path.normcase(str(resolved))
        basis = f"path:{normalized_path}"
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


def _contains_secret(payload: dict) -> bool:
    return bool(SECRET_PATTERN.search(json.dumps(payload, ensure_ascii=False, sort_keys=True)))


def _validate_utc(value: object, field: str) -> None:
    if not isinstance(value, str) or not UTC_TIMESTAMP_PATTERN.fullmatch(value):
        raise ValidationError(f"{field} must be a UTC ISO-8601 timestamp ending in Z")
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValidationError(f"{field} is not a valid timestamp") from exc


def _string_list(value: object, field: str, *, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, list) or (not allow_empty and not value):
        qualifier = "" if allow_empty else " non-empty"
        raise ValidationError(f"{field} must be a{qualifier} list")
    normalized: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValidationError(f"{field} values must be non-empty strings")
        cleaned = " ".join(item.split())
        if cleaned not in normalized:
            normalized.append(cleaned)
    return normalized


def _workspace_root(knowledge_root: Path) -> Path:
    return ensure_within(knowledge_root / WORKSPACE_DIR_NAME, knowledge_root)


def _workspace_project_path(project_key: str, knowledge_root: Path) -> Path:
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{2,80}", project_key):
        raise ValidationError("Invalid workspace project key")
    return ensure_within(_workspace_root(knowledge_root) / "projects" / f"{project_key}.json", knowledge_root)


def _route_id(route: dict) -> str:
    parts = (
        " ".join(str(route.get("title", "")).casefold().split()),
        "\0".join(str(item).casefold() for item in route.get("project_keys", [])),
        "\0".join(str(item).casefold() for item in route.get("triggers", [])),
    )
    return hashlib.sha256("\0".join(parts).encode("utf-8")).hexdigest()[:20]


def _workspace_route_path(route_id: str, knowledge_root: Path) -> Path:
    if not re.fullmatch(r"[0-9a-f]{20}", route_id):
        raise ValidationError("Invalid workspace route id")
    return ensure_within(_workspace_root(knowledge_root) / "routes" / f"{route_id}.json", knowledge_root)


def validate_workspace_project(record: dict, *, stored: bool = True) -> None:
    if not isinstance(record, dict):
        raise ValidationError("Workspace project must be a JSON object")
    if _contains_secret(record):
        raise ValidationError("Workspace project contains secret-like content")
    required = {
        "schema_version",
        "record_type",
        "project_key",
        "display_name",
        "root",
        "remote",
        "aliases",
        "domains",
        "purpose",
        "operator_hints",
        "entry_points",
        "codegraph",
        "policy",
        "metadata_basis",
        "verified_at",
        "status",
    }
    missing = sorted(required - record.keys())
    if missing:
        raise ValidationError(f"Workspace project is missing fields: {', '.join(missing)}")
    if record["schema_version"] != SCHEMA_VERSION or record["record_type"] != "workspace-project":
        raise ValidationError("Unsupported workspace project schema")
    if not isinstance(record["project_key"], str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{2,80}", record["project_key"]):
        raise ValidationError("Invalid workspace project key")
    if not isinstance(record["display_name"], str) or not record["display_name"].strip():
        raise ValidationError("display_name must be a non-empty string")
    if not isinstance(record["root"], str) or not Path(record["root"]).is_absolute():
        raise ValidationError("root must be an absolute path")
    if record["remote"] is not None:
        if not isinstance(record["remote"], str) or normalize_remote(record["remote"]) != record["remote"]:
            raise ValidationError("remote must be normalized")
    _string_list(record["aliases"], "aliases")
    _string_list(record["domains"], "domains")
    _string_list(record["operator_hints"], "operator_hints", allow_empty=True)
    if not isinstance(record["purpose"], str) or not record["purpose"].strip():
        raise ValidationError("purpose must be a non-empty string")
    if record["metadata_basis"] != "filesystem-and-git":
        raise ValidationError("Unsupported metadata_basis")
    if record["status"] not in ALLOWED_STATUSES:
        raise ValidationError("Unsupported workspace project status")
    _validate_utc(record["verified_at"], "verified_at")
    codegraph = record["codegraph"]
    if not isinstance(codegraph, dict) or set(codegraph) != {"path", "present"}:
        raise ValidationError("codegraph must contain path and present")
    if not isinstance(codegraph["path"], str) or not isinstance(codegraph["present"], bool):
        raise ValidationError("Invalid codegraph metadata")
    policy = record["policy"]
    if not isinstance(policy, dict) or set(policy) != {"path", "exists", "sha256"}:
        raise ValidationError("policy must contain path, exists, and sha256")
    if not isinstance(policy["path"], str) or not Path(policy["path"]).is_absolute():
        raise ValidationError("policy.path must be absolute")
    if not isinstance(policy["exists"], bool):
        raise ValidationError("policy.exists must be boolean")
    if policy["exists"]:
        if not isinstance(policy["sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", policy["sha256"]):
            raise ValidationError("policy.sha256 is invalid")
    elif policy["sha256"] is not None:
        raise ValidationError("Missing policy cannot have a sha256")
    entry_points = record["entry_points"]
    if not isinstance(entry_points, list) or not entry_points:
        raise ValidationError("entry_points must be a non-empty list")
    seen_paths: set[str] = set()
    for entry_point in entry_points:
        if not isinstance(entry_point, dict):
            raise ValidationError("entry_points values must be objects")
        required_entry_point = {
            "path",
            "aliases",
            "domains",
            "purpose",
            "operator_hints",
            "codegraph",
            "policy",
        }
        if set(entry_point) != required_entry_point:
            raise ValidationError("Workspace entry point has unsupported fields")
        entry_path = entry_point["path"]
        if not isinstance(entry_path, str) or not Path(entry_path).is_absolute() or entry_path in seen_paths:
            raise ValidationError("Workspace entry point paths must be unique absolute paths")
        seen_paths.add(entry_path)
        _string_list(entry_point["aliases"], "entry_points.aliases")
        _string_list(entry_point["domains"], "entry_points.domains")
        _string_list(entry_point["operator_hints"], "entry_points.operator_hints", allow_empty=True)
        if not isinstance(entry_point["purpose"], str) or not entry_point["purpose"].strip():
            raise ValidationError("entry_points.purpose must be a non-empty string")
        if not isinstance(entry_point["codegraph"], dict) or set(entry_point["codegraph"]) != {"path", "present"}:
            raise ValidationError("entry_points.codegraph must contain path and present")
        if not isinstance(entry_point["codegraph"]["path"], str) or not isinstance(entry_point["codegraph"]["present"], bool):
            raise ValidationError("Invalid entry point codegraph metadata")
        entry_policy = entry_point["policy"]
        if not isinstance(entry_policy, dict) or set(entry_policy) != {"path", "exists", "sha256"}:
            raise ValidationError("entry_points.policy must contain path, exists, and sha256")


def register_workspace_project(
    project_root: Path,
    knowledge_root: Path,
    *,
    aliases: list[str],
    domains: list[str],
    purpose: str,
    operator_hints: list[str],
) -> dict:
    requested_root = project_root.expanduser().resolve(strict=True)
    root = _git_toplevel(requested_root) or requested_root
    identity = resolve_project(root)
    policy_path = root / "AGENTS.md"
    policy_exists = policy_path.is_file()
    entry_policy_path = requested_root / "AGENTS.md"
    entry_policy_exists = entry_policy_path.is_file()
    entry_point = {
        "path": str(requested_root),
        "aliases": _string_list(aliases, "aliases"),
        "domains": _string_list(domains, "domains"),
        "purpose": " ".join(purpose.split()),
        "operator_hints": _string_list(operator_hints, "operator_hints", allow_empty=True),
        "codegraph": {
            "path": str(requested_root / ".codegraph"),
            "present": (requested_root / ".codegraph").is_dir(),
        },
        "policy": {
            "path": str(entry_policy_path),
            "exists": entry_policy_exists,
            "sha256": sha256_file(entry_policy_path) if entry_policy_exists else None,
        },
    }
    path = _workspace_project_path(identity.key, knowledge_root)
    existing = json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
    if existing:
        validate_workspace_project(existing)
        existing_entry_points = [item for item in existing["entry_points"] if item["path"] != str(requested_root)]
        entry_points = existing_entry_points + [entry_point]
        aliases = _string_list(existing["aliases"] + entry_point["aliases"], "aliases")
        domains = _string_list(existing["domains"] + entry_point["domains"], "domains")
        hints = _string_list(
            existing["operator_hints"] + entry_point["operator_hints"],
            "operator_hints",
            allow_empty=True,
        )
        top_level_purpose = existing["purpose"]
    else:
        entry_points = [entry_point]
        aliases = entry_point["aliases"]
        domains = entry_point["domains"]
        hints = entry_point["operator_hints"]
        top_level_purpose = entry_point["purpose"]
    payload = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "workspace-project",
        "project_key": identity.key,
        "display_name": identity.display_name,
        "root": identity.root,
        "remote": identity.remote,
        "aliases": aliases,
        "domains": domains,
        "purpose": top_level_purpose,
        "operator_hints": hints,
        "entry_points": entry_points,
        "codegraph": {"path": str(root / ".codegraph"), "present": (root / ".codegraph").is_dir()},
        "policy": {
            "path": str(policy_path),
            "exists": policy_exists,
            "sha256": sha256_file(policy_path) if policy_exists else None,
        },
        "metadata_basis": "filesystem-and-git",
        "verified_at": utc_now(),
        "status": "current",
    }
    validate_workspace_project(payload)
    action = "refreshed" if path.exists() else "added"
    atomic_write_json(path, payload)
    return {
        "store": "project-knowledge",
        "record_type": "workspace-project",
        "project_key": identity.key,
        "title": identity.display_name,
        "action": action,
        "path": str(path),
    }


def _registered_workspace_projects(knowledge_root: Path) -> dict[str, dict]:
    projects_dir = ensure_within(_workspace_root(knowledge_root) / "projects", knowledge_root)
    projects: dict[str, dict] = {}
    if not projects_dir.is_dir():
        return projects
    for path in sorted(projects_dir.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        validate_workspace_project(payload)
        if path.stem != payload["project_key"]:
            raise ValidationError("Workspace project key does not match its filename")
        projects[payload["project_key"]] = payload
    return projects


def validate_workspace_route(route: dict, knowledge_root: Path, *, stored: bool = False) -> None:
    if not isinstance(route, dict):
        raise ValidationError("Workspace route must be a JSON object")
    if _contains_secret(route):
        raise ValidationError("Workspace route contains secret-like content")
    required = {
        "schema_version",
        "record_type",
        "title",
        "triggers",
        "project_keys",
        "guidance",
        "basis",
        "evidence",
        "verified_at",
        "status",
    }
    if stored:
        required.add("route_id")
    missing = sorted(required - route.keys())
    if missing:
        raise ValidationError(f"Workspace route is missing fields: {', '.join(missing)}")
    if route["schema_version"] != SCHEMA_VERSION or route["record_type"] != "workspace-route":
        raise ValidationError("Unsupported workspace route schema")
    if not isinstance(route["title"], str) or not route["title"].strip():
        raise ValidationError("title must be a non-empty string")
    project_keys = _string_list(route["project_keys"], "project_keys")
    _string_list(route["triggers"], "triggers")
    if not isinstance(route["guidance"], str) or not route["guidance"].strip():
        raise ValidationError("guidance must be a non-empty string")
    if route["basis"] not in ALLOWED_ROUTE_BASES:
        raise ValidationError("Unsupported workspace route basis")
    if route["status"] not in ALLOWED_STATUSES:
        raise ValidationError("Unsupported workspace route status")
    _validate_utc(route["verified_at"], "verified_at")
    registered = _registered_workspace_projects(knowledge_root)
    if any(project_key not in registered for project_key in project_keys):
        raise ValidationError("Workspace route references an unregistered project")
    evidence = route["evidence"]
    if not isinstance(evidence, list):
        raise ValidationError("evidence must be a list")
    if route["basis"] == "operator-provided" and evidence:
        raise ValidationError("Operator-provided routes cannot masquerade as code-verified")
    if route["basis"] == "code-verified":
        covered: set[str] = set()
        for item in evidence:
            if not isinstance(item, dict):
                raise ValidationError("Route evidence must be an object")
            required_evidence = {"project_key", "path", "symbol", "line_start", "line_end", "sha256"}
            if required_evidence - item.keys():
                raise ValidationError("Route evidence is missing required fields")
            project_key = item["project_key"]
            if project_key not in project_keys:
                raise ValidationError("Route evidence belongs to an unrelated project")
            project_root = Path(registered[project_key]["root"])
            relative = _relative_path(item["path"], "evidence.path")
            source = ensure_within(project_root.joinpath(*relative.parts), project_root)
            if relative.suffix.casefold() in DOCUMENT_EXTENSIONS or not source.is_file():
                raise ValidationError("Route evidence must reference current code or machine-parsed artifacts")
            if not isinstance(item["symbol"], str) or not item["symbol"].strip():
                raise ValidationError("Route evidence symbol must be non-empty")
            if not isinstance(item["line_start"], int) or not isinstance(item["line_end"], int):
                raise ValidationError("Route evidence lines must be integers")
            if item["line_start"] < 1 or item["line_end"] < item["line_start"]:
                raise ValidationError("Route evidence line range is invalid")
            if item["line_end"] > len(source.read_bytes().splitlines()):
                raise ValidationError("Route evidence line range exceeds the file")
            if not isinstance(item["sha256"], str) or sha256_file(source) != item["sha256"]:
                raise ValidationError("Route evidence hash does not match current source")
            covered.add(project_key)
        if covered != set(project_keys):
            raise ValidationError("Code-verified routes require current evidence from every project")
    expected_id = _route_id(route)
    if stored and route.get("route_id") != expected_id:
        raise ValidationError("route_id is not deterministic for this route")


def upsert_workspace_route(route: dict, knowledge_root: Path) -> dict:
    payload = dict(route)
    payload["route_id"] = _route_id(payload)
    payload.setdefault("verified_at", utc_now())
    validate_workspace_route(payload, knowledge_root, stored=True)
    path = _workspace_route_path(payload["route_id"], knowledge_root)
    action = "refreshed" if path.exists() else "added"
    atomic_write_json(path, payload)
    return {
        "store": "project-knowledge",
        "record_type": "workspace-route",
        "record_id": payload["route_id"],
        "title": payload["title"],
        "action": action,
        "path": str(path),
    }


def query_workspace(knowledge_root: Path, *, text: str = "") -> dict[str, list[dict]]:
    needle = text.casefold().strip()
    projects = list(_registered_workspace_projects(knowledge_root).values())
    routes: list[dict] = []
    routes_dir = ensure_within(_workspace_root(knowledge_root) / "routes", knowledge_root)
    if routes_dir.is_dir():
        for path in sorted(routes_dir.glob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            validate_workspace_route(payload, knowledge_root, stored=True)
            if path.stem != payload["route_id"]:
                raise ValidationError("Workspace route id does not match its filename")
            routes.append(payload)
    if needle:
        projects = [item for item in projects if needle in json.dumps(item, ensure_ascii=False).casefold()]
        routes = [item for item in routes if needle in json.dumps(item, ensure_ascii=False).casefold()]
    return {
        "projects": sorted(projects, key=lambda item: (item["display_name"], item["project_key"])),
        "routes": sorted(routes, key=lambda item: (item["title"], item["route_id"])),
    }


def revalidate_workspace(knowledge_root: Path, *, write: bool = True) -> dict:
    result = {"checked": 0, "changed": 0, "would_change": 0, "maintenance": []}
    for project_key, payload in _registered_workspace_projects(knowledge_root).items():
        result["checked"] += 1
        if payload["status"] != "current":
            continue
        root = Path(payload["root"])
        valid = root.is_dir()
        if valid:
            try:
                identity = resolve_project(root)
                valid = identity.key == project_key and identity.remote == payload["remote"]
            except (OSError, ValueError):
                valid = False
        if valid:
            codegraph_path = root / ".codegraph"
            valid = codegraph_path.is_dir() == payload["codegraph"]["present"]
        if valid:
            policy_path = root / "AGENTS.md"
            policy_exists = policy_path.is_file()
            valid = policy_exists == payload["policy"]["exists"]
            if valid and policy_exists:
                valid = sha256_file(policy_path) == payload["policy"]["sha256"]
        if valid:
            for entry_point in payload["entry_points"]:
                entry_root = Path(entry_point["path"])
                if not entry_root.is_dir():
                    valid = False
                    break
                if (entry_root / ".codegraph").is_dir() != entry_point["codegraph"]["present"]:
                    valid = False
                    break
                entry_policy = entry_root / "AGENTS.md"
                entry_policy_exists = entry_policy.is_file()
                if entry_policy_exists != entry_point["policy"]["exists"]:
                    valid = False
                    break
                if entry_policy_exists and sha256_file(entry_policy) != entry_point["policy"]["sha256"]:
                    valid = False
                    break
        if not valid:
            result["would_change"] += 1
            result["maintenance"].append(
                {"record_type": "workspace-project", "record_id": project_key, "action": "needs-reverification"}
            )
            if write:
                payload["status"] = "needs-reverification"
                atomic_write_json(_workspace_project_path(project_key, knowledge_root), payload)
                result["changed"] += 1
    return result


def _entry_id(entry: dict, project_key: str) -> str:
    evidence = entry.get("evidence") or [{}]
    primary = evidence[0]
    parts = (
        project_key,
        str(entry.get("kind", "")),
        " ".join(str(entry.get("title", "")).casefold().split()),
        " ".join(str(entry.get("claim", "")).casefold().split()),
        str(primary.get("path", "")),
        str(primary.get("symbol", "")),
    )
    return hashlib.sha256("\0".join(parts).encode("utf-8")).hexdigest()[:20]


def validate_entry(
    entry: dict,
    project_key: str,
    project_root: Path,
    *,
    check_hash: bool = True,
    check_files: bool = True,
    stored: bool = False,
) -> None:
    if not isinstance(entry, dict):
        raise ValidationError("Entry must be a JSON object")
    if _contains_secret(entry):
        raise ValidationError("Entry contains secret-like content")
    required = {"schema_version", "kind", "title", "claim", "scope", "evidence", "verified_at", "status"}
    if stored:
        required.update({"entry_id", "project_key"})
    missing = sorted(required - entry.keys())
    if missing:
        raise ValidationError(f"Entry is missing required fields: {', '.join(missing)}")
    if entry["schema_version"] != SCHEMA_VERSION:
        raise ValidationError("Unsupported schema_version")
    if entry["status"] not in ALLOWED_STATUSES:
        raise ValidationError("Unsupported status")
    if not isinstance(entry["kind"], str) or entry["kind"] not in ALLOWED_ENTRY_KINDS:
        raise ValidationError("Unsupported knowledge kind")
    if entry.get("project_key") not in {None, project_key}:
        raise ValidationError("project_key does not match the current project")
    if not isinstance(entry["title"], str) or not entry["title"].strip():
        raise ValidationError("title must be a non-empty string")
    if not isinstance(entry["claim"], str) or not entry["claim"].strip():
        raise ValidationError("claim must be a non-empty string")
    if not isinstance(entry["scope"], list) or not entry["scope"]:
        raise ValidationError("scope must be a non-empty list")
    if not isinstance(entry["verified_at"], str) or not UTC_TIMESTAMP_PATTERN.fullmatch(entry["verified_at"]):
        raise ValidationError("verified_at must be a UTC ISO-8601 timestamp ending in Z")
    try:
        datetime.fromisoformat(entry["verified_at"].replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValidationError("verified_at is not a valid timestamp") from exc
    project_root = project_root.resolve(strict=True)
    scope_paths: set[str] = set()
    for scope_path in entry["scope"]:
        if not isinstance(scope_path, str):
            raise ValidationError("scope values must be strings")
        relative_scope = _relative_path(scope_path, "scope")
        normalized_scope = relative_scope.as_posix()
        scope_paths.add(normalized_scope)
        resolved_scope = ensure_within(project_root.joinpath(*relative_scope.parts), project_root)
        if check_files and not resolved_scope.is_file():
            raise ValidationError("scope must reference an existing project file")
    evidence_items = entry["evidence"]
    if not isinstance(evidence_items, list) or not evidence_items:
        raise ValidationError("Source evidence is required")
    for evidence in evidence_items:
        if not isinstance(evidence, dict):
            raise ValidationError("Evidence must be an object")
        required_evidence = {"kind", "path", "symbol", "line_start", "line_end", "sha256"}
        missing_evidence = sorted(required_evidence - evidence.keys())
        if missing_evidence:
            raise ValidationError(f"Evidence is missing fields: {', '.join(missing_evidence)}")
        if evidence["kind"] not in ALLOWED_EVIDENCE_KINDS:
            raise ValidationError("Evidence kind is not executable or parseable source")
        if not isinstance(evidence["path"], str):
            raise ValidationError("Evidence path must be a string")
        relative = _relative_path(evidence["path"], "evidence.path")
        if relative.as_posix() not in scope_paths:
            raise ValidationError("Every evidence path must be included in scope")
        if relative.suffix.casefold() in DOCUMENT_EXTENSIONS:
            raise ValidationError("Documentation cannot be used as project fact evidence")
        source_path = ensure_within(project_root.joinpath(*relative.parts), project_root)
        if not isinstance(evidence["symbol"], str) or not evidence["symbol"].strip():
            raise ValidationError("Evidence symbol must be a non-empty string")
        if not isinstance(evidence["line_start"], int) or not isinstance(evidence["line_end"], int):
            raise ValidationError("Evidence lines must be integers")
        if evidence["line_start"] < 1 or evidence["line_end"] < evidence["line_start"]:
            raise ValidationError("Evidence line range is invalid")
        digest = str(evidence["sha256"])
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValidationError("Evidence sha256 is invalid")
        if not source_path.is_file():
            if check_files:
                raise ValidationError("Evidence file does not exist")
            continue
        if check_files:
            line_count = len(source_path.read_bytes().splitlines())
            if evidence["line_end"] > line_count:
                raise ValidationError("Evidence line range exceeds the referenced file")
        if check_hash and entry["status"] == "current" and sha256_file(source_path) != digest:
            raise ValidationError("Evidence hash does not match current source")
    expected_id = _entry_id(entry, project_key)
    if stored and entry.get("entry_id") != expected_id:
        raise ValidationError("entry_id is not deterministic for this entry")
    if not stored and entry.get("entry_id") not in {None, expected_id}:
        raise ValidationError("entry_id is not deterministic for this entry")


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


def upsert_entry(entry: dict, project_root: Path, knowledge_root: Path) -> Path:
    identity = resolve_project(project_root)
    payload = dict(entry)
    payload["project_key"] = identity.key
    payload["entry_id"] = _entry_id(payload, identity.key)
    payload.setdefault("verified_at", utc_now())
    validate_entry(payload, identity.key, Path(identity.root), stored=True)

    project_dir = ensure_within(knowledge_root / identity.key, knowledge_root)
    entry_path = ensure_within(project_dir / "entries" / f"{payload['entry_id']}.json", knowledge_root)
    project_path = ensure_within(project_dir / "project.json", knowledge_root)
    project_payload = {"schema_version": SCHEMA_VERSION, **asdict(identity)}
    if project_path.exists():
        existing_project = json.loads(project_path.read_text(encoding="utf-8"))
        if existing_project.get("key") != identity.key:
            raise ValidationError("Existing project metadata does not match the current project")
        if existing_project.get("remote") != identity.remote:
            raise ValidationError("Existing project metadata remote does not match the current project")
    else:
        atomic_write_json(project_path, project_payload)
    atomic_write_json(entry_path, payload)
    return entry_path


def query_entries(project_key: str, knowledge_root: Path, filters: dict) -> list[dict]:
    project_dir = ensure_within(knowledge_root / project_key, knowledge_root)
    entries_dir = ensure_within(project_dir / "entries", knowledge_root)
    if not entries_dir.is_dir():
        return []
    results: list[dict] = []
    text_filter = str(filters.get("text", "")).casefold()
    for path in sorted(entries_dir.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("project_key") != project_key:
            raise ValidationError("Stored entry belongs to another project")
        if filters.get("status") and payload.get("status") != filters["status"]:
            continue
        evidence = payload.get("evidence", [])
        if filters.get("path") and not any(item.get("path") == filters["path"] for item in evidence):
            continue
        if filters.get("symbol") and not any(item.get("symbol") == filters["symbol"] for item in evidence):
            continue
        if text_filter and text_filter not in json.dumps(payload, ensure_ascii=False).casefold():
            continue
        results.append(payload)
    return sorted(results, key=lambda item: (item.get("title", ""), item.get("entry_id", "")))


def revalidate_entries(project_root: Path, knowledge_root: Path, *, write: bool = True) -> dict[str, int]:
    identity = resolve_project(project_root)
    project_dir = ensure_within(knowledge_root / identity.key, knowledge_root)
    entries_dir = ensure_within(project_dir / "entries", knowledge_root)
    result = {"checked": 0, "changed": 0, "would_change": 0, "stale_entries": []}
    if not entries_dir.is_dir():
        return result
    for path in sorted(entries_dir.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        validate_entry(
            payload,
            identity.key,
            Path(identity.root),
            check_hash=False,
            check_files=False,
            stored=True,
        )
        result["checked"] += 1
        if payload["status"] != "current":
            continue
        valid = True
        for evidence in payload["evidence"]:
            relative = _relative_path(evidence["path"], "evidence.path")
            source = ensure_within(Path(identity.root).joinpath(*relative.parts), Path(identity.root))
            if not source.is_file() or sha256_file(source) != evidence["sha256"]:
                valid = False
                break
        if not valid:
            result["would_change"] += 1
            result["stale_entries"].append(payload["entry_id"])
            if write:
                payload["status"] = "needs-reverification"
                atomic_write_json(path, payload)
                result["changed"] += 1
    return result


def validate_store(knowledge_root: Path, project_root: Path | None = None) -> dict[str, int]:
    counts = {"projects": 0, "entries": 0, "workspace_projects": 0, "workspace_routes": 0}
    expected_key = resolve_project(project_root).key if project_root else None
    if not knowledge_root.is_dir():
        return counts
    for project_dir in sorted(path for path in knowledge_root.iterdir() if path.is_dir()):
        ensure_within(project_dir, knowledge_root)
        if project_dir.name == WORKSPACE_DIR_NAME:
            continue
        if expected_key and project_dir.name != expected_key:
            continue
        metadata = json.loads((project_dir / "project.json").read_text(encoding="utf-8"))
        if metadata.get("project_key", metadata.get("key")) != project_dir.name:
            raise ValidationError("Project metadata key does not match its directory")
        counts["projects"] += 1
        validation_root = Path(metadata.get("root", ""))
        check_files = validation_root.is_dir()
        if project_root is not None and project_dir.name == expected_key:
            validation_root = project_root.resolve(strict=True)
            check_files = True
        elif not check_files:
            validation_root = project_dir
        for entry_path in sorted((project_dir / "entries").glob("*.json")):
            payload = json.loads(entry_path.read_text(encoding="utf-8"))
            validate_entry(
                payload,
                project_dir.name,
                validation_root,
                check_hash=project_root is not None and project_dir.name == expected_key,
                check_files=check_files,
                stored=True,
            )
            counts["entries"] += 1
    workspace_projects = _registered_workspace_projects(knowledge_root)
    counts["workspace_projects"] = len(workspace_projects)
    routes_dir = ensure_within(_workspace_root(knowledge_root) / "routes", knowledge_root)
    if routes_dir.is_dir():
        for route_path in sorted(routes_dir.glob("*.json")):
            payload = json.loads(route_path.read_text(encoding="utf-8"))
            validate_workspace_route(payload, knowledge_root, stored=True)
            if route_path.stem != payload["route_id"]:
                raise ValidationError("Workspace route id does not match its filename")
            counts["workspace_routes"] += 1
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Maintain source-grounded project knowledge.")
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
        help="Report stale entries without modifying stored knowledge",
    )
    workspace_register = subparsers.add_parser("workspace-register")
    workspace_register.add_argument("--project-root", required=True, type=Path)
    workspace_register.add_argument("--alias", action="append", required=True)
    workspace_register.add_argument("--domain", action="append", required=True)
    workspace_register.add_argument("--purpose", required=True)
    workspace_register.add_argument("--hint", action="append", default=[])
    workspace_query = subparsers.add_parser("workspace-query")
    workspace_query.add_argument("--text", default="")
    workspace_route = subparsers.add_parser("workspace-upsert-route")
    workspace_route.add_argument("--candidate", required=True, help="JSON file path, or - for stdin")
    workspace_revalidate = subparsers.add_parser("workspace-revalidate")
    workspace_revalidate.add_argument(
        "--check-only",
        action="store_true",
        help="Report stale workspace records without modifying stored knowledge",
    )
    validate = subparsers.add_parser("validate")
    validate.add_argument("--project-root", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "resolve-project":
            output = asdict(resolve_project(args.project_root))
        elif args.command == "query":
            identity = resolve_project(args.project_root)
            filters = {name: getattr(args, name) for name in ("text", "path", "symbol", "status")}
            output = query_entries(identity.key, args.knowledge_root, filters)
        elif args.command == "upsert":
            candidate = load_candidate(args.candidate)
            output = {"path": str(upsert_entry(candidate, args.project_root, args.knowledge_root))}
        elif args.command == "revalidate":
            output = revalidate_entries(args.project_root, args.knowledge_root, write=not args.check_only)
        elif args.command == "workspace-register":
            output = register_workspace_project(
                args.project_root,
                args.knowledge_root,
                aliases=args.alias,
                domains=args.domain,
                purpose=args.purpose,
                operator_hints=args.hint,
            )
        elif args.command == "workspace-query":
            output = query_workspace(args.knowledge_root, text=args.text)
        elif args.command == "workspace-upsert-route":
            output = upsert_workspace_route(load_candidate(args.candidate), args.knowledge_root)
        elif args.command == "workspace-revalidate":
            output = revalidate_workspace(args.knowledge_root, write=not args.check_only)
        else:
            output = validate_store(args.knowledge_root, args.project_root)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())


