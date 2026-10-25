from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path, PurePosixPath


ALLOWED_SKILLS = {
    "grounding-project-knowledge",
    "avoiding-project-pitfalls",
}
ALLOWED_OPERATIONS = {"create", "update", "atomic-replace", "temp-cleanup"}
POLICY_MARKERS = (
    "Self-Maintaining Knowledge Exception",
    "grounding-project-knowledge\\knowledge\\projects\\**",
    "avoiding-project-pitfalls\\knowledge\\projects\\**",
    "schema-validated",
    "durable knowledge records",
    "SKILL.md",
    "reparse point",
    "does not bypass platform",
)


def is_exempt(target: str, operation: str, content_class: str) -> bool:
    normalized = target.replace("\\", "/")
    path = PurePosixPath(normalized)
    parts = path.parts
    if path.is_absolute() or ".." in parts or "." in parts:
        return False
    if len(parts) < 5:
        return False
    if parts[0] not in ALLOWED_SKILLS or parts[1:3] != ("knowledge", "projects"):
        return False
    if operation not in ALLOWED_OPERATIONS:
        return False
    if operation == "temp-cleanup":
        return content_class == "tool-owned-temporary" and parts[-1].endswith(".tmp")
    return content_class == "validated-knowledge"


def validate_policy(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    normalized = " ".join(text.split())
    return [marker for marker in POLICY_MARKERS if marker not in normalized]


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the knowledge-maintenance confirmation exception.")
    parser.add_argument("--cases", required=True, type=Path)
    args = parser.parse_args()

    skill_root = Path(__file__).resolve().parents[1]
    codex_root = Path(__file__).resolve().parents[3]
    policy_files = (codex_root / "AGENTS.md", skill_root / "SKILL.md")
    failures: list[str] = []

    for policy_file in policy_files:
        missing = validate_policy(policy_file)
        if missing:
            failures.append(f"{policy_file}: missing policy markers: {', '.join(missing)}")

    cases = json.loads(args.cases.read_text(encoding="utf-8"))
    for index, case in enumerate(cases, start=1):
        actual = is_exempt(case["target"], case["operation"], case["content_class"])
        if actual is not case["expected"]:
            failures.append(
                f"case {index}: expected {case['expected']} for "
                f"{case['operation']} {case['target']}, got {actual}"
            )

    if failures:
        print("FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print(f"PASS: {len(cases)} cases and {len(policy_files)} policy files validated")
    return 0


if __name__ == "__main__":
    sys.exit(main())


