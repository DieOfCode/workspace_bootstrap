#!/usr/bin/env python3
"""Create a non-destructive Orca/OpenSpec project scaffold."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create missing agent workflow and memory files without overwriting existing files."
    )
    parser.add_argument("--project", default=".", help="Repository root (default: current directory)")
    parser.add_argument("--project-name", help="Name used in generated templates")
    parser.add_argument("--dry-run", action="store_true", help="Print planned actions without writing")
    parser.add_argument("--json", action="store_true", help="Print the final report as JSON")
    parser.add_argument(
        "--init-openspec",
        action="store_true",
        help="Initialize OpenSpec with the installed official CLI when absent",
    )
    parser.add_argument(
        "--openspec-tools",
        default="agents",
        help="Comma-separated OpenSpec tool IDs (default: agents)",
    )
    parser.add_argument("--language", help="OpenSpec artifact language for a new installation")
    return parser.parse_args()


def render(text: str, project_name: str) -> str:
    return text.replace("{{PROJECT_NAME}}", project_name).replace("{{DATE}}", date.today().isoformat())


def collect_templates(template_root: Path) -> list[Path]:
    return sorted(path for path in template_root.rglob("*") if path.is_file())


def scaffold(project: Path, template_root: Path, project_name: str, dry_run: bool) -> dict:
    report: dict[str, list[str]] = {"created": [], "preserved": [], "planned": []}
    for source in collect_templates(template_root):
        relative = source.relative_to(template_root)
        target = project / relative
        if target.exists():
            report["preserved"].append(str(relative))
            continue
        if dry_run:
            report["planned"].append(str(relative))
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render(source.read_text(encoding="utf-8"), project_name), encoding="utf-8")
        report["created"].append(str(relative))

    for relative in (
        Path("docs/agent-memory/active/.gitkeep"),
        Path("docs/agent-memory/completed/.gitkeep"),
        Path("docs/agent-memory/decisions/.gitkeep"),
    ):
        target = project / relative
        if target.exists():
            report["preserved"].append(str(relative))
        elif dry_run:
            report["planned"].append(str(relative))
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("", encoding="utf-8")
            report["created"].append(str(relative))
    return report


def init_openspec(project: Path, args: argparse.Namespace, report: dict) -> int:
    if not args.init_openspec:
        report["openspec"] = {"status": "not-requested"}
        return 0
    if (project / "openspec").exists():
        report["openspec"] = {"status": "preserved", "path": "openspec"}
        return 0
    executable = shutil.which("openspec")
    if executable is None:
        report["openspec"] = {
            "status": "missing-cli",
            "next": "Install the official @fission-ai/openspec CLI with user approval, then rerun.",
        }
        return 2

    command = [
        executable,
        "init",
        str(project),
        "--tools",
        args.openspec_tools,
        "--profile",
        "core",
        "--no-animation",
        "--no-copilot-cloud",
    ]
    if args.language:
        command.extend(["--language", args.language])
    if args.dry_run:
        report["openspec"] = {"status": "planned", "command": command}
        return 0

    completed = subprocess.run(command, check=False)
    report["openspec"] = {"status": "initialized" if completed.returncode == 0 else "failed"}
    return completed.returncode


def print_report(report: dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return
    for key in ("planned", "created", "preserved"):
        values = report.get(key, [])
        if values:
            print(f"{key}:")
            for value in values:
                print(f"  - {value}")
    openspec = report.get("openspec")
    if openspec:
        print(f"openspec: {openspec['status']}")
        if "next" in openspec:
            print(f"next: {openspec['next']}")


def main() -> int:
    args = parse_args()
    project = Path(args.project).expanduser().resolve()
    if not project.is_dir():
        print(f"error: project directory does not exist: {project}", file=sys.stderr)
        return 1

    skill_root = Path(__file__).resolve().parent.parent
    template_root = skill_root / "assets" / "project"
    if not template_root.is_dir():
        print(f"error: template directory is missing: {template_root}", file=sys.stderr)
        return 1

    project_name = args.project_name or project.name
    report = scaffold(project, template_root, project_name, args.dry_run)
    openspec_code = init_openspec(project, args, report)
    print_report(report, args.json)
    return openspec_code


if __name__ == "__main__":
    raise SystemExit(main())
