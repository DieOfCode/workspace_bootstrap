#!/usr/bin/env python3
"""CLI for preparing and maintaining a local Orca agent workspace."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from workspace_lib import ACTIVE_DIR, WorkspaceError, bootstrap, compact, complete, conflicts, doctor, exit_code, risk, scan_secrets, validate_workspace


class WorkspaceArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise WorkspaceError(message)


def add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--project", default=".", help="Project root (default: current directory)")
    parser.add_argument("--json", action="store_true", help="Print the stable JSON envelope")


def build_parser() -> argparse.ArgumentParser:
    parser = WorkspaceArgumentParser(description="Manage a local-only Orca agent workspace."); subs = parser.add_subparsers(dest="command", required=True, parser_class=WorkspaceArgumentParser)
    cmd = subs.add_parser("bootstrap"); add_common(cmd); cmd.add_argument("--project-name"); cmd.add_argument("--dry-run", action="store_true"); cmd.add_argument("--init-openspec", action="store_true"); cmd.add_argument("--openspec-tools", default="agents")
    cmd = subs.add_parser("doctor"); add_common(cmd); cmd.add_argument("--apply", action="store_true"); cmd.add_argument("--write-report", action="store_true")
    cmd = subs.add_parser("risk"); add_common(cmd); cmd.add_argument("--task", required=True); cmd.add_argument("--apply", action="store_true")
    cmd = subs.add_parser("conflicts"); add_common(cmd); cmd.add_argument("--candidate", required=True); cmd.add_argument("--active-dir")
    cmd = subs.add_parser("complete"); add_common(cmd); cmd.add_argument("--task", required=True); cmd.add_argument("--outcome", required=True); cmd.add_argument("--completed-at")
    cmd = subs.add_parser("compact"); add_common(cmd); cmd.add_argument("--as-of"); cmd.add_argument("--older-than-days", type=int, default=30); cmd.add_argument("--dry-run", action="store_true")
    cmd = subs.add_parser("scan-secrets"); add_common(cmd); cmd.add_argument("--paths", nargs="*")
    cmd = subs.add_parser("validate"); add_common(cmd)
    return parser


def human_output(result: dict) -> None:
    print(f"{result.get('command')}: {'OK' if result.get('ok') else 'BLOCKED'}")
    for item in result.get("findings", []): print(f"[{item['severity']}] {item['code']}: {item['message']}")
    for item in result.get("changes", []): print(f"{item['action']}: {item.get('path') or ' '.join(item.get('command', []))}")


def main(argv: Optional[list[str]] = None) -> int:
    raw_args = list(argv) if argv is not None else sys.argv[1:]
    command = raw_args[0] if raw_args and not raw_args[0].startswith("-") else "unknown"
    json_output = "--json" in raw_args
    try:
        args = build_parser().parse_args(raw_args); project = Path(args.project).expanduser().resolve(); skill_root = Path(__file__).resolve().parent.parent
        if args.command == "bootstrap": result = bootstrap(project, skill_root / "assets" / "project", args.project_name, args.dry_run, args.init_openspec, args.openspec_tools)
        elif args.command == "doctor": result = doctor(project, args.apply, args.write_report)
        elif args.command == "risk": result = risk(project, Path(args.task).expanduser().resolve(), args.apply)
        elif args.command == "conflicts": result = conflicts(project, Path(args.candidate).expanduser().resolve(), Path(args.active_dir).expanduser().resolve() if args.active_dir else project / ACTIVE_DIR)
        elif args.command == "complete": result = complete(project, Path(args.task).expanduser().resolve(), args.outcome, args.completed_at)
        elif args.command == "compact": result = compact(project, args.as_of, args.older_than_days, args.dry_run)
        elif args.command == "scan-secrets": result = scan_secrets(project, args.paths)
        elif args.command == "validate": result = validate_workspace(project)
        else: raise WorkspaceError(f"Unknown command: {args.command}")
    except WorkspaceError as exc:
        result = {"schema_version": 1, "command": command, "ok": False, "findings": [{"severity": "error", "code": "operational_error", "message": str(exc)}], "changes": [], "data": {}}; code = 1
    else: code = exit_code(result)
    print(json.dumps(result, ensure_ascii=False, indent=2)) if json_output else human_output(result)
    return code


if __name__ == "__main__": raise SystemExit(main())
