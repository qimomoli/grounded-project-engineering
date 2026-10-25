from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from . import __version__
from .repository import RepositoryError, find_repo_root, install_skills, validate_repository


def _test_commands(root: Path) -> tuple[list[str], ...]:
    return (
        [
            sys.executable,
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests",
            "-p",
            "test_*.py",
            "-v",
        ],
        [
            sys.executable,
            "-m",
            "unittest",
            "discover",
            "-s",
            "skills/grounding-project-knowledge/scripts",
            "-p",
            "test_*.py",
            "-v",
        ],
        [
            sys.executable,
            "-m",
            "unittest",
            "discover",
            "-s",
            "skills/avoiding-project-pitfalls/scripts",
            "-p",
            "test_*.py",
            "-v",
        ],
        [
            sys.executable,
            "skills/confirm-before-work/evals/validate.py",
            "--cases",
            "skills/confirm-before-work/evals/cases.json",
        ],
    )


def _run_tests(root: Path) -> int:
    errors = validate_repository(root)
    if errors:
        print("FAIL: repository validation")
        for error in errors:
            print(f"- {error}")
        return 1
    for command in _test_commands(root):
        print("$ " + " ".join(command))
        completed = subprocess.run(command, cwd=root, check=False)
        if completed.returncode:
            return completed.returncode
    print("PASS: repository validation and all configured test suites")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gpe",
        description="Validate, test, and install the Grounded Project Engineering skills.",
    )
    parser.add_argument("--version", action="version", version=__version__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate", help="validate repository structure")
    validate_parser.add_argument("--source", type=Path, help="repository root")

    test_parser = subparsers.add_parser("test", help="run configured repository checks")
    test_parser.add_argument("--source", type=Path, help="repository root")

    install_parser = subparsers.add_parser("install", help="install complete Skill directories")
    install_parser.add_argument("--source", type=Path, help="repository root")
    install_parser.add_argument("--target", type=Path, required=True, help="Skill root directory")
    install_parser.add_argument("--skill", action="append", dest="skills", help="skill name; repeatable")
    install_parser.add_argument("--force", action="store_true", help="overlay existing destinations")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "install":
            installed = install_skills(
                args.source or Path.cwd(),
                args.target,
                skills=tuple(args.skills) if args.skills else None,
                force=args.force,
            )
            for path in installed:
                print(f"INSTALLED {path}")
            return 0

        root = find_repo_root(args.source)
        if args.command == "validate":
            errors = validate_repository(root)
            if errors:
                print("FAIL")
                for error in errors:
                    print(f"- {error}")
                return 1
            print("PASS: repository structure valid")
            return 0
        if args.command == "test":
            return _run_tests(root)
    except (OSError, RepositoryError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 2
