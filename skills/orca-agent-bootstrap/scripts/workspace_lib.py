#!/usr/bin/env python3
"""Dependency-free implementation for the Orca local agent workspace CLI."""

from __future__ import annotations

import glob
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import tempfile
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional


SCHEMA_VERSION = 1
WORKSPACE_DIR = Path(".agent-workspace")
POLICY_PATH = WORKSPACE_DIR / "policy.json"
ACTIVE_DIR = WORKSPACE_DIR / "memory" / "active"
COMPLETED_DIR = WORKSPACE_DIR / "memory" / "completed"
RAW_DIR = COMPLETED_DIR / "raw"
RECORDS_DIR = COMPLETED_DIR / "records"
ROLLUPS_DIR = COMPLETED_DIR / "rollups"
DECISIONS_DIR = WORKSPACE_DIR / "memory" / "decisions"
VERIFICATIONS_DIR = WORKSPACE_DIR / "memory" / "verifications"
REPORTS_DIR = WORKSPACE_DIR / "reports"
TEMPLATES_DIR = WORKSPACE_DIR / "templates"

SERVICE_PATHS = ("AGENTS.md", "MEMORY.md", "openspec", ".agents", ".agent-workspace")
IGNORE_PATTERNS = ("/AGENTS.md", "/MEMORY.md", "/openspec/", "/.agents/", "/.agent-workspace/")
IGNORE_BEGIN = "# workspace-bootstrap: local agent workspace"
IGNORE_END = "# workspace-bootstrap: end"
ACTIVE_STATUSES = {"ready", "dispatched", "blocked", "verifying", "rework", "accepted"}
ACTIVE_TRANSITIONS = {
    "ready": {"dispatched", "blocked"},
    "dispatched": {"blocked", "verifying"},
    "blocked": {"ready", "dispatched", "rework"},
    "verifying": {"accepted", "blocked", "rework"},
    "rework": {"dispatched", "blocked", "verifying"},
    "accepted": set(),
}
OUTCOMES = {"accepted", "partial", "superseded", "abandoned"}
RISK_LEVELS = {"low", "medium", "high"}
ROUTING_PROFILES = {"coordinator", "executor-standard", "executor-complex", "verifier", "specialist"}


class WorkspaceError(Exception):
    """Operational or input error (exit code 1)."""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def envelope(command: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "command": command,
        "ok": True,
        "findings": [],
        "changes": [],
        "data": {},
    }


def finding(result: dict[str, Any], severity: str, code: str, message: str, **extra: Any) -> None:
    item = {"severity": severity, "code": code, "message": message}
    item.update({key: value for key, value in extra.items() if value is not None})
    result["findings"].append(item)
    if severity in {"error", "blocking"}:
        result["ok"] = False


def exit_code(result: dict[str, Any]) -> int:
    return 0 if result.get("ok", False) else 2


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        handle.write(content)
        temporary = Path(handle.name)
    os.replace(temporary, path)


def atomic_write_json(path: Path, value: Any) -> None:
    atomic_write_text(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise WorkspaceError(f"JSON file does not exist: {path}") from exc
    except json.JSONDecodeError as exc:
        raise WorkspaceError(f"Invalid JSON in {path}: {exc}") from exc


def require_within(path: Path, parent: Path, label: str) -> None:
    try:
        path.resolve().relative_to(parent.resolve())
    except ValueError as exc:
        raise WorkspaceError(f"{label} must be inside {parent}") from exc


def run_command(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)


def is_git_repository(project: Path) -> bool:
    completed = run_command(["git", "rev-parse", "--is-inside-work-tree"], project)
    return completed.returncode == 0 and completed.stdout.strip() == "true"


def tracked_service_files(project: Path) -> list[str]:
    if not is_git_repository(project):
        return []
    completed = run_command(["git", "ls-files", "-z", "--", *SERVICE_PATHS], project)
    if completed.returncode != 0:
        raise WorkspaceError(completed.stderr.strip() or "git ls-files failed")
    return sorted(item for item in completed.stdout.split("\0") if item)


def parse_gitignore_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip() and not line.lstrip().startswith("#")]


def ensure_gitignore(project: Path, dry_run: bool = False) -> tuple[bool, str]:
    path = project / ".gitignore"
    original = path.read_text(encoding="utf-8") if path.exists() else ""
    lines = original.splitlines()
    try:
        begin_index = lines.index(IGNORE_BEGIN)
        end_index = lines.index(IGNORE_END, begin_index + 1)
    except ValueError:
        begin_index = end_index = -1
    outside = lines if begin_index < 0 else lines[:begin_index] + lines[end_index + 1 :]
    outside_patterns = {line.strip() for line in outside if line.strip() and not line.lstrip().startswith("#")}
    managed_patterns = [pattern for pattern in IGNORE_PATTERNS if pattern not in outside_patterns]
    block = [IGNORE_BEGIN, *managed_patterns, IGNORE_END]
    if begin_index >= 0:
        updated_lines = lines[:begin_index] + block + lines[end_index + 1 :]
    else:
        updated_lines = list(lines)
        if updated_lines and updated_lines[-1] != "":
            updated_lines.append("")
        updated_lines.extend(block)
    updated = "\n".join(updated_lines).rstrip("\n") + "\n"
    changed = updated != original
    if changed and not dry_run:
        atomic_write_text(path, updated)
    return changed, updated


def gitignore_has_required_patterns(project: Path) -> tuple[bool, list[str]]:
    path = project / ".gitignore"
    if not path.exists():
        return False, list(IGNORE_PATTERNS)
    patterns = set(parse_gitignore_lines(path.read_text(encoding="utf-8")))
    missing = [pattern for pattern in IGNORE_PATTERNS if pattern not in patterns]
    return not missing, missing


def existing_service_paths_are_ignored(project: Path) -> list[str]:
    if not is_git_repository(project):
        return []
    missing: list[str] = []
    for relative in SERVICE_PATHS:
        target = project / relative
        if not target.exists():
            continue
        completed = run_command(["git", "check-ignore", "-q", "--", relative], project)
        if completed.returncode != 0:
            missing.append(relative)
    return missing


def planned_service_paths_are_ignored(project: Path) -> list[str]:
    if not is_git_repository(project):
        return []
    representatives = (
        "AGENTS.md",
        "MEMORY.md",
        "openspec/.workspace-bootstrap-check",
        ".agents/.workspace-bootstrap-check",
        ".agent-workspace/policy.json",
    )
    missing = []
    for relative in representatives:
        completed = run_command(["git", "check-ignore", "--no-index", "-q", "--", relative], project)
        if completed.returncode != 0:
            missing.append(relative)
    return missing


def render_template(text: str, project_name: str) -> str:
    return text.replace("{{PROJECT_NAME}}", project_name).replace("{{DATE}}", date.today().isoformat())


def collect_template_files(template_root: Path) -> list[Path]:
    return sorted(path for path in template_root.rglob("*") if path.is_file())


def bootstrap(project: Path, template_root: Path, project_name: Optional[str] = None, dry_run: bool = False,
              init_openspec: bool = False, openspec_tools: str = "none") -> dict[str, Any]:
    result = envelope("bootstrap")
    project = project.resolve()
    if not project.is_dir():
        raise WorkspaceError(f"Project directory does not exist: {project}")
    if not template_root.is_dir():
        raise WorkspaceError(f"Template directory does not exist: {template_root}")
    tracked = tracked_service_files(project)
    if tracked:
        finding(result, "blocking", "tracked_service_files",
                "Agent workspace files are already tracked; bootstrap will not untrack them automatically.",
                paths=tracked, suggested_command="git rm -r --cached -- " + " ".join(repr(path) for path in tracked))
        result["data"]["tracked_service_files"] = tracked
        return result
    gitignore_changed, _ = ensure_gitignore(project, dry_run=dry_run)
    if gitignore_changed:
        result["changes"].append({"action": "plan" if dry_run else "update", "path": ".gitignore"})
    if not dry_run:
        not_ignored = planned_service_paths_are_ignored(project)
        if not_ignored:
            finding(result, "blocking", "gitignore_check_failed",
                    "Managed service paths are not covered by Git ignore rules; no service files were created.",
                    paths=not_ignored)
            return result
    name = project_name or project.name
    for source in collect_template_files(template_root):
        relative = source.relative_to(template_root)
        target = project / relative
        if target.exists():
            result["changes"].append({"action": "preserve", "path": str(relative)})
            continue
        result["changes"].append({"action": "plan" if dry_run else "create", "path": str(relative)})
        if not dry_run:
            atomic_write_text(target, render_template(source.read_text(encoding="utf-8"), name))
    directories = (REPORTS_DIR, ACTIVE_DIR, RAW_DIR, RECORDS_DIR, ROLLUPS_DIR, DECISIONS_DIR, VERIFICATIONS_DIR, TEMPLATES_DIR)
    for relative in directories:
        target = project / relative
        if not target.exists():
            result["changes"].append({"action": "plan" if dry_run else "create-directory", "path": str(relative)})
            if not dry_run:
                target.mkdir(parents=True, exist_ok=True)
    if init_openspec:
        if openspec_tools != "none":
            finding(result, "error", "nonlocal_openspec_tools",
                    "Local-only mode requires OpenSpec --tools none; project-local agent guidance is installed under .agents/.")
            result["data"].update({"project": str(project), "local_only": True})
            return result
        openspec_dir = project / "openspec"
        if openspec_dir.exists():
            result["changes"].append({"action": "preserve", "path": "openspec"})
        else:
            executable = shutil.which("openspec")
            if executable is None:
                finding(result, "error", "missing_openspec_cli", "OpenSpec CLI is required for --init-openspec.")
            else:
                command = [executable, "init", str(project), "--tools", openspec_tools, "--profile", "core"]
                if dry_run:
                    result["changes"].append({"action": "plan-command", "command": command})
                else:
                    completed = run_command(command, project)
                    if completed.returncode != 0:
                        finding(result, "error", "openspec_init_failed",
                                completed.stderr.strip() or completed.stdout.strip() or "openspec init failed")
                    else:
                        result["changes"].append({"action": "initialize", "path": "openspec"})
    result["data"].update({"project": str(project), "local_only": True})
    return result


def command_fact(command: str, source: str, confidence: str) -> dict[str, str]:
    return {"command": command, "source": source, "confidence": confidence}


def add_unique_fact(bucket: list[dict[str, str]], fact: dict[str, str]) -> None:
    if not any(item["command"] == fact["command"] for item in bucket):
        bucket.append(fact)


def detect_project(project: Path) -> dict[str, Any]:
    stacks: list[dict[str, str]] = []
    commands: dict[str, list[dict[str, str]]] = {key: [] for key in ("setup", "build", "test", "lint", "format")}
    def stack(name: str, evidence: str) -> None:
        if not any(item["name"] == name for item in stacks):
            stacks.append({"name": name, "evidence": evidence})
    package_json = project / "package.json"
    if package_json.exists():
        stack("node", "package.json")
        try:
            package = read_json(package_json)
        except WorkspaceError:
            package = {}
        scripts = package.get("scripts", {}) if isinstance(package, dict) else {}
        runner, test_runner = "npm run", "npm test"
        if (project / "pnpm-lock.yaml").exists():
            add_unique_fact(commands["setup"], command_fact("pnpm install --frozen-lockfile", "pnpm-lock.yaml", "high")); runner, test_runner = "pnpm", "pnpm test"
        elif (project / "yarn.lock").exists():
            add_unique_fact(commands["setup"], command_fact("yarn install --frozen-lockfile", "yarn.lock", "high")); runner, test_runner = "yarn", "yarn test"
        elif (project / "bun.lockb").exists() or (project / "bun.lock").exists():
            add_unique_fact(commands["setup"], command_fact("bun install --frozen-lockfile", "bun.lock", "high")); runner, test_runner = "bun run", "bun test"
        elif (project / "package-lock.json").exists():
            add_unique_fact(commands["setup"], command_fact("npm ci", "package-lock.json", "high"))
        else:
            add_unique_fact(commands["setup"], command_fact("npm install", "package.json", "medium"))
        for name, bucket in (("build", "build"), ("lint", "lint"), ("format", "format")):
            if name in scripts:
                add_unique_fact(commands[bucket], command_fact(f"{runner} {name}", f"package.json#scripts.{name}", "high"))
        if "test" in scripts:
            add_unique_fact(commands["test"], command_fact(test_runner, "package.json#scripts.test", "high"))
    python_markers = [path for path in (project / "pyproject.toml", project / "setup.py", project / "setup.cfg") if path.exists()]
    if python_markers or (project / "requirements.txt").exists():
        evidence = python_markers[0].name if python_markers else "requirements.txt"; stack("python", evidence)
        if (project / "requirements.txt").exists():
            add_unique_fact(commands["setup"], command_fact("python -m pip install -r requirements.txt", "requirements.txt", "high"))
        elif python_markers:
            add_unique_fact(commands["setup"], command_fact("python -m pip install -e .", evidence, "medium"))
        py_text = "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in python_markers)
        if "pytest" in py_text or (project / "pytest.ini").exists():
            add_unique_fact(commands["test"], command_fact("python -m pytest", evidence, "high"))
        elif (project / "tests").is_dir():
            add_unique_fact(commands["test"], command_fact("python -m unittest discover", "tests/", "medium"))
        if "ruff" in py_text:
            add_unique_fact(commands["lint"], command_fact("ruff check .", evidence, "high")); add_unique_fact(commands["format"], command_fact("ruff format .", evidence, "high"))
    if (project / "go.mod").exists():
        stack("go", "go.mod"); add_unique_fact(commands["setup"], command_fact("go mod download", "go.mod", "high")); add_unique_fact(commands["build"], command_fact("go build ./...", "go.mod", "high")); add_unique_fact(commands["test"], command_fact("go test ./...", "go.mod", "high"))
    if (project / "Cargo.toml").exists():
        stack("rust", "Cargo.toml"); add_unique_fact(commands["build"], command_fact("cargo build", "Cargo.toml", "high")); add_unique_fact(commands["test"], command_fact("cargo test", "Cargo.toml", "high")); add_unique_fact(commands["lint"], command_fact("cargo clippy --all-targets --all-features", "Cargo.toml", "high")); add_unique_fact(commands["format"], command_fact("cargo fmt --check", "Cargo.toml", "high"))
    gradle = "./gradlew" if (project / "gradlew").exists() else "gradle"
    if any(project.glob("build.gradle*")) or (project / "settings.gradle").exists() or (project / "settings.gradle.kts").exists():
        stack("jvm-gradle", "build.gradle/settings.gradle"); add_unique_fact(commands["build"], command_fact(f"{gradle} build", "Gradle files", "high" if gradle.startswith("./") else "medium")); add_unique_fact(commands["test"], command_fact(f"{gradle} test", "Gradle files", "high" if gradle.startswith("./") else "medium"))
    if (project / "pom.xml").exists():
        stack("jvm-maven", "pom.xml"); mvn = "./mvnw" if (project / "mvnw").exists() else "mvn"; add_unique_fact(commands["build"], command_fact(f"{mvn} package", "pom.xml", "high" if mvn.startswith("./") else "medium")); add_unique_fact(commands["test"], command_fact(f"{mvn} test", "pom.xml", "high" if mvn.startswith("./") else "medium"))
    if (project / "Package.swift").exists():
        stack("swift-package", "Package.swift"); add_unique_fact(commands["build"], command_fact("swift build", "Package.swift", "high")); add_unique_fact(commands["test"], command_fact("swift test", "Package.swift", "high"))
    if list(project.glob("*.xcodeproj")) or list(project.glob("*.xcworkspace")):
        stack("xcode", "*.xcodeproj/*.xcworkspace")
    pubspec = project / "pubspec.yaml"
    if pubspec.exists():
        text = pubspec.read_text(encoding="utf-8", errors="ignore")
        if re.search(r"^\s*flutter\s*:", text, re.MULTILINE):
            stack("flutter", "pubspec.yaml"); add_unique_fact(commands["setup"], command_fact("flutter pub get", "pubspec.yaml", "high")); add_unique_fact(commands["test"], command_fact("flutter test", "pubspec.yaml", "high")); add_unique_fact(commands["lint"], command_fact("flutter analyze", "pubspec.yaml", "high"))
        else:
            stack("dart", "pubspec.yaml"); add_unique_fact(commands["setup"], command_fact("dart pub get", "pubspec.yaml", "high")); add_unique_fact(commands["test"], command_fact("dart test", "pubspec.yaml", "high")); add_unique_fact(commands["lint"], command_fact("dart analyze", "pubspec.yaml", "high"))
    for filename, tool in (("Makefile", "make"), ("justfile", "just"), ("Justfile", "just")):
        path = project / filename
        if path.exists():
            stack(tool, filename); text = path.read_text(encoding="utf-8", errors="ignore"); targets = set(re.findall(r"^([A-Za-z0-9_.-]+):", text, re.MULTILINE))
            for target, bucket in (("setup", "setup"), ("build", "build"), ("test", "test"), ("lint", "lint"), ("format", "format")):
                if target in targets: add_unique_fact(commands[bucket], command_fact(f"{tool} {target}", filename, "high"))
    return {"stacks": stacks, "commands": commands}


def update_command_placeholders(path: Path, commands: dict[str, list[dict[str, str]]]) -> bool:
    if not path.exists(): return False
    original = path.read_text(encoding="utf-8"); updated = original
    for key, label in {"setup": "Setup", "build": "Build", "test": "Test", "lint": "Lint/format"}.items():
        facts = commands.get(key, []) or (commands.get("format", []) if key == "lint" else [])
        if facts:
            updated = re.sub(rf"^- {re.escape(label)}: `\[verified command\]`$", f"- {label}: `{facts[0]['command']}`", updated, flags=re.MULTILINE)
    if updated != original: atomic_write_text(path, updated); return True
    return False


def doctor(project: Path, apply: bool = False, write_report: bool = False) -> dict[str, Any]:
    result = envelope("doctor"); detected = detect_project(project); result["data"] = detected
    if not detected["stacks"]: finding(result, "warning", "no_stack_detected", "No supported project stack was detected.")
    for category in ("build", "test"):
        if not detected["commands"][category]: finding(result, "warning", f"missing_{category}_command", f"No {category} command was detected.")
    if apply:
        policy_path = project / POLICY_PATH; policy = read_json(policy_path)
        policy["project"] = {"name": project.name, **detected, "doctor_updated_at": utc_now()}; atomic_write_json(policy_path, policy)
        result["changes"].append({"action": "update", "path": str(POLICY_PATH)})
        for relative in (Path("AGENTS.md"), Path("MEMORY.md")):
            if update_command_placeholders(project / relative, detected["commands"]): result["changes"].append({"action": "update-placeholders", "path": str(relative)})
    if write_report:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"); report_path = project / REPORTS_DIR / f"doctor-{stamp}.json"; atomic_write_json(report_path, result); result["changes"].append({"action": "create", "path": str(report_path.relative_to(project))})
    return result


def validate_policy(policy: Any) -> list[str]:
    if not isinstance(policy, dict): return ["policy must be a JSON object"]
    errors = []
    if policy.get("schema_version") != SCHEMA_VERSION: errors.append(f"schema_version must be {SCHEMA_VERSION}")
    for key in ("project", "orchestration", "memory", "secrets"):
        if not isinstance(policy.get(key), dict): errors.append(f"{key} must be an object")
    if policy.get("orchestration", {}).get("verifier_mode") != "explicit-only": errors.append("orchestration.verifier_mode must be explicit-only")
    configured_transitions = policy.get("orchestration", {}).get("active_state_transitions")
    expected_transitions = {key: sorted(value) for key, value in ACTIVE_TRANSITIONS.items()}
    normalized_transitions = {key: sorted(value) for key, value in configured_transitions.items()} if isinstance(configured_transitions, dict) and all(isinstance(value, list) for value in configured_transitions.values()) else None
    if normalized_transitions != expected_transitions: errors.append("orchestration.active_state_transitions does not match the supported state machine")
    if policy.get("memory", {}).get("rollup_after_days") != 30: errors.append("memory.rollup_after_days must be 30")
    if policy.get("memory", {}).get("keep_raw") is not True: errors.append("memory.keep_raw must be true")
    return errors


def validate_task(task: Any) -> list[str]:
    if not isinstance(task, dict): return ["task must be a JSON object"]
    errors = []
    if task.get("schema_version") != SCHEMA_VERSION: errors.append(f"schema_version must be {SCHEMA_VERSION}")
    if not isinstance(task.get("task_key"), str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]*", task.get("task_key", "")): errors.append("task_key must use lowercase kebab-case")
    status = task.get("status")
    if status not in ACTIVE_STATUSES: errors.append(f"status must be one of {sorted(ACTIVE_STATUSES)}")
    if task.get("task_type") not in {"coordinator", "executor", "verifier", "specialist"}: errors.append("task_type must be coordinator, executor, verifier, or specialist")
    if task.get("owner") is not None and not isinstance(task.get("owner"), str): errors.append("owner must be a string or null")
    timestamps = task.get("timestamps")
    if not isinstance(timestamps, dict): errors.append("timestamps must be an object")
    else:
        for key in ("created", "updated"):
            try: parse_timestamp(timestamps.get(key))
            except WorkspaceError: errors.append(f"timestamps.{key} must be an ISO timestamp")
    if task.get("risk", {}).get("level") not in RISK_LEVELS: errors.append(f"risk.level must be one of {sorted(RISK_LEVELS)}")
    if task.get("routing", {}).get("profile") not in ROUTING_PROFILES: errors.append(f"routing.profile must be one of {sorted(ROUTING_PROFILES)}")
    scope = task.get("scope")
    if not isinstance(scope, dict): errors.append("scope must be an object")
    else:
        for key in ("read", "write", "forbidden"):
            if not isinstance(scope.get(key), list): errors.append(f"scope.{key} must be an array")
    for key in ("dependencies", "acceptance_criteria", "evidence", "blockers"):
        if not isinstance(task.get(key), list): errors.append(f"{key} must be an array")
    if not isinstance(task.get("verification"), dict): errors.append("verification must be an object")
    if not isinstance(task.get("verifier_requested"), bool): errors.append("verifier_requested must be a boolean")
    routing = task.get("routing")
    if not isinstance(routing, dict): errors.append("routing must be an object")
    else:
        for key in ("requested", "effective"):
            choice = routing.get(key)
            if not isinstance(choice, dict): errors.append(f"routing.{key} must be an object")
            else:
                for field in ("agent", "model", "effort"):
                    if choice.get(field) is not None and not isinstance(choice.get(field), str): errors.append(f"routing.{key}.{field} must be a string or null")
    history = task.get("state_history")
    if not isinstance(history, list) or not history: errors.append("state_history must be a non-empty array")
    else:
        history_statuses = []
        for index, entry in enumerate(history):
            if not isinstance(entry, dict) or entry.get("status") not in ACTIVE_STATUSES:
                errors.append(f"state_history[{index}].status is invalid"); continue
            history_statuses.append(entry["status"])
            try: parse_timestamp(entry.get("at"))
            except WorkspaceError: errors.append(f"state_history[{index}].at must be an ISO timestamp")
        if history_statuses and history_statuses[0] != "ready": errors.append("state_history must start with ready")
        for previous, current in zip(history_statuses, history_statuses[1:]):
            if current not in ACTIVE_TRANSITIONS.get(previous, set()): errors.append(f"invalid state transition: {previous} -> {current}")
        if history_statuses and status in ACTIVE_STATUSES and history_statuses[-1] != status: errors.append("state_history must end with the current status")
    return errors


HIGH_RISK_TERMS = {"auth", "authentication", "authorization", "permission", "secret", "credential", "token", "payment", "billing", "invoice", "migration", "delete", "destructive", "encryption", "crypto", "concurrency", "race", "deployment", "production", "security", "public api", "schema change"}
MEDIUM_RISK_TERMS = {"dependency", "performance", "cache", "database", "api", "refactor", "cross-module", "user-visible"}


def assess_risk(task: dict[str, Any]) -> dict[str, Any]:
    errors = validate_task(task)
    if errors: raise WorkspaceError("Invalid task: " + "; ".join(errors))
    corpus = json.dumps(task, ensure_ascii=False).lower(); high = sorted(term for term in HIGH_RISK_TERMS if term in corpus); medium = sorted(term for term in MEDIUM_RISK_TERMS if term in corpus); write_count = len(task.get("scope", {}).get("write", [])); dependency_count = len(task.get("dependencies", []))
    if high or write_count > 10:
        level = "high"; reasons = [f"high-risk term: {term}" for term in high] + (["write scope exceeds 10 patterns"] if write_count > 10 else [])
    elif medium or write_count > 4 or dependency_count > 2:
        level = "medium"; reasons = [f"medium-risk term: {term}" for term in medium] + (["write scope exceeds 4 patterns"] if write_count > 4 else []) + (["task has more than 2 dependencies"] if dependency_count > 2 else [])
    else:
        level = "low"; reasons = ["bounded scope with no elevated risk signals"]
    task_type = task.get("task_type", "executor")
    if task_type == "coordinator": profile = "coordinator"
    elif task_type == "verifier": profile = "verifier"
    elif task_type == "specialist": profile = "specialist"
    else: profile = "executor-complex" if level == "high" else "executor-standard"
    return {"level": level, "reasons": reasons, "routing_profile": profile, "verifier_recommended": level == "high", "verifier_requested": bool(task.get("verifier_requested", False))}


def risk(project: Path, task_path: Path, apply: bool = False) -> dict[str, Any]:
    result = envelope("risk"); task = read_json(task_path); assessment = assess_risk(task); result["data"] = assessment
    if assessment["verifier_recommended"] and not assessment["verifier_requested"]: finding(result, "warning", "verifier_recommended", "High-risk task would benefit from an explicit independent verifier.")
    if apply:
        require_within(task_path, project / ACTIVE_DIR, "Applied task")
        task["risk"] = {"level": assessment["level"], "reasons": assessment["reasons"]}; task.setdefault("routing", {})["profile"] = assessment["routing_profile"]; task.setdefault("timestamps", {})["updated"] = utc_now(); atomic_write_json(task_path, task); result["changes"].append({"action": "update", "path": str(task_path.relative_to(project))})
    return result


def normalize_pattern(pattern: str) -> str:
    value = pattern.replace("\\", "/")
    while value.startswith("./"): value = value[2:]
    if not value or value.startswith("/") or ".." in Path(value).parts: raise WorkspaceError(f"Unsafe or empty scope pattern: {pattern}")
    return value.rstrip("/")


def has_glob(pattern: str) -> bool: return any(character in pattern for character in "*?[")


def expand_pattern(project: Path, pattern: str) -> set[str]:
    normalized = normalize_pattern(pattern)
    if not has_glob(normalized):
        target = project / normalized
        if target.is_dir(): return {str(path.relative_to(project)).replace("\\", "/") for path in target.rglob("*") if path.is_file()}
        return {normalized}
    return {str(Path(match).resolve().relative_to(project.resolve())).replace("\\", "/") for match in glob.glob(str(project / normalized), recursive=True) if Path(match).is_file()}


def static_prefix(pattern: str) -> str:
    parts = []
    for part in normalize_pattern(pattern).split("/"):
        if has_glob(part): break
        parts.append(part)
    return "/".join(parts)


def pattern_relation(project: Path, left: str, right: str) -> tuple[str, list[str]]:
    left_norm, right_norm = normalize_pattern(left), normalize_pattern(right); intersection = sorted(expand_pattern(project, left_norm) & expand_pattern(project, right_norm))
    if intersection: return "definite", intersection
    if not has_glob(left_norm) and not has_glob(right_norm):
        if left_norm == right_norm or left_norm.startswith(right_norm + "/") or right_norm.startswith(left_norm + "/"): return "definite", [left_norm if len(left_norm) >= len(right_norm) else right_norm]
        return "none", []
    left_prefix, right_prefix = static_prefix(left_norm), static_prefix(right_norm)
    if not left_prefix or not right_prefix: return "potential", []
    if left_prefix == right_prefix or left_prefix.startswith(right_prefix + "/") or right_prefix.startswith(left_prefix + "/"): return "potential", []
    return "none", []


def conflicts(project: Path, candidate_path: Path, active_dir: Optional[Path] = None) -> dict[str, Any]:
    result = envelope("conflicts"); candidate = read_json(candidate_path); errors = validate_task(candidate)
    if errors: raise WorkspaceError("Invalid candidate task: " + "; ".join(errors))
    directory = active_dir or (project / ACTIVE_DIR); definite = []; potential = []; worktree_violations = []
    for path in sorted(directory.glob("*.json")) if directory.exists() else []:
        if path.resolve() == candidate_path.resolve(): continue
        other = read_json(path); other_errors = validate_task(other)
        if other_errors: finding(result, "warning", "invalid_active_task", "; ".join(other_errors), path=str(path)); continue
        other_has_definite = False; other_has_potential = False
        for left in candidate["scope"]["write"]:
            for right in other["scope"]["write"]:
                relation, files = pattern_relation(project, left, right); item = {"task_key": other["task_key"], "candidate_pattern": left, "active_pattern": right}
                if relation == "definite": item["files"] = files; definite.append(item); other_has_definite = True
                elif relation == "potential": potential.append(item); other_has_potential = True
        if candidate["scope"]["write"] and other["scope"]["write"] and not other_has_definite and not other_has_potential:
            candidate_worktree = candidate.get("orca", {}).get("worktree"); active_worktree = other.get("orca", {}).get("worktree")
            if not candidate_worktree or not active_worktree or candidate_worktree == active_worktree:
                worktree_violations.append({"task_key": other["task_key"], "candidate_worktree": candidate_worktree, "active_worktree": active_worktree})
    dependencies = sorted({item["task_key"] for item in definite})
    if definite: finding(result, "blocking", "write_scope_overlap", "Definite write overlap requires sequential execution.", conflicts=definite, recommended_dependencies=dependencies)
    if potential: finding(result, "warning", "potential_write_scope_overlap", "Glob scopes may overlap; refine the write sets before parallel dispatch.", conflicts=potential)
    if worktree_violations: finding(result, "blocking", "parallel_worktree_required", "Parallel writers require distinct non-empty worktree identifiers.", tasks=worktree_violations)
    result["data"] = {"definite": definite, "potential": potential, "worktree_violations": worktree_violations, "recommended_dependencies": dependencies}; return result


def parse_timestamp(value: str) -> datetime:
    if not isinstance(value, str): raise WorkspaceError(f"Invalid ISO timestamp: {value}")
    try: return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc: raise WorkspaceError(f"Invalid ISO timestamp: {value}") from exc


def bullet_lines(items: Iterable[Any], empty: str = "- None recorded") -> str:
    values = list(items); return "\n".join(f"- {item if isinstance(item, str) else json.dumps(item, ensure_ascii=False)}" for item in values) if values else empty


def completion_markdown(task: dict[str, Any], outcome: str, completed_at: str) -> str:
    openspec = task.get("openspec", {}); orca = task.get("orca", {}); route = task.get("routing", {})
    return f"""# Completed task: {task['task_key']}

- Outcome: {outcome}
- Completed: {completed_at}
- Owner: {task.get('owner') or 'unassigned'}
- OpenSpec change/task: {openspec.get('change') or 'none'} / {openspec.get('task') or 'none'}
- Orca Task/Dispatch: {orca.get('task_id') or 'none'} / {orca.get('dispatch_id') or 'none'}
- Effective agent/model/effort: {json.dumps(route.get('effective') or {}, ensure_ascii=False)}

## Result

{task.get('result_summary') or 'No result summary recorded.'}

## Changed areas

{bullet_lines(task.get('scope', {}).get('write', []))}

## Acceptance evidence

{bullet_lines(task.get('evidence', []))}

## Decisions

{bullet_lines(task.get('decisions', []))}

## Residual risks and follow-ups

{bullet_lines(task.get('residual_risks', []))}
"""


def complete(project: Path, task_path: Path, outcome: str, completed_at: Optional[str] = None) -> dict[str, Any]:
    result = envelope("complete")
    if outcome not in OUTCOMES: raise WorkspaceError(f"Outcome must be one of {sorted(OUTCOMES)}")
    require_within(task_path, project / ACTIVE_DIR, "Completed task")
    task = read_json(task_path); errors = validate_task(task)
    if errors: raise WorkspaceError("Invalid task: " + "; ".join(errors))
    if outcome == "accepted" and (not task.get("acceptance_criteria") or not task.get("evidence")): finding(result, "blocking", "missing_acceptance_evidence", "Accepted tasks require acceptance criteria and evidence."); return result
    if outcome == "accepted" and task.get("status") != "accepted": finding(result, "blocking", "task_not_accepted", "An accepted outcome requires the active task status to be accepted."); return result
    timestamp = completed_at or utc_now(); completed_dt = parse_timestamp(timestamp); month = completed_dt.strftime("%Y-%m"); task_key = task["task_key"]; raw_path = project / RAW_DIR / month / f"{task_key}.json"; record_path = project / RECORDS_DIR / month / f"{task_key}.md"
    if raw_path.exists() or record_path.exists(): finding(result, "blocking", "completion_exists", "Completion artifacts already exist; existing records will not be overwritten."); return result
    task["state_history"].append({"status": "completed", "at": timestamp, "reason": f"Task closed with outcome {outcome}"}); task["status"] = "completed"; task["outcome"] = outcome; task["completed_at"] = timestamp; task.setdefault("timestamps", {})["updated"] = timestamp
    atomic_write_json(raw_path, task); atomic_write_text(record_path, completion_markdown(task, outcome, timestamp)); task_path.unlink()
    result["changes"].extend([{"action": "create", "path": str(raw_path.relative_to(project))}, {"action": "create", "path": str(record_path.relative_to(project))}, {"action": "remove-after-archive", "path": str(task_path.relative_to(project))}]); result["data"] = {"task_key": task_key, "outcome": outcome, "completed_at": timestamp}; return result


def rollup_markdown(month: str, tasks: list[dict[str, Any]]) -> str:
    source_through = max(task.get("completed_at", "unknown") for task in tasks)
    lines = [f"# Completed task rollup: {month}", "", f"Source: {len(tasks)} raw record(s) through {source_through}", ""]
    for task in sorted(tasks, key=lambda item: item["task_key"]):
        lines.extend([f"## {task['task_key']}", "", f"- Outcome: {task.get('outcome', 'unknown')}", f"- Completed: {task.get('completed_at', 'unknown')}", f"- Risk: {task.get('risk', {}).get('level', 'unknown')}", f"- Result: {task.get('result_summary') or 'No result summary recorded.'}", f"- Evidence: {len(task.get('evidence', []))} item(s)", f"- Decisions: {len(task.get('decisions', []))} item(s)", f"- Residual risks: {len(task.get('residual_risks', []))} item(s)", ""])
    return "\n".join(lines).rstrip() + "\n"


def compact(project: Path, as_of: Optional[str] = None, older_than_days: int = 30, dry_run: bool = False) -> dict[str, Any]:
    result = envelope("compact"); reference = parse_timestamp(as_of) if as_of else datetime.now(timezone.utc); grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for path in sorted((project / RAW_DIR).glob("*/*.json")) if (project / RAW_DIR).exists() else []:
        task = read_json(path); completed = parse_timestamp(task.get("completed_at", ""))
        if (reference - completed).days >= older_than_days: grouped[completed.strftime("%Y-%m")].append(task)
    for month, tasks in sorted(grouped.items()):
        target = project / ROLLUPS_DIR / f"{month}.md"; content = rollup_markdown(month, tasks); existed = target.exists()
        if existed and target.read_text(encoding="utf-8") == content: result["changes"].append({"action": "preserve", "path": str(target.relative_to(project))})
        elif dry_run: result["changes"].append({"action": "plan", "path": str(target.relative_to(project)), "tasks": len(tasks)})
        else: atomic_write_text(target, content); result["changes"].append({"action": "update" if existed else "create", "path": str(target.relative_to(project)), "tasks": len(tasks)})
    result["data"] = {"eligible_months": sorted(grouped), "older_than_days": older_than_days, "raw_records_preserved": True}; return result


SECRET_RULES = (("private-key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")), ("aws-access-key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")), ("github-token", re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b")), ("slack-token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b")), ("stripe-secret", re.compile(r"\bsk_(?:live|test)_[A-Za-z0-9]{20,}\b")))
GENERIC_SECRET = re.compile(r"(?i)\b(api[_-]?key|client[_-]?secret|secret|token|password|passwd)\b\s*[:=]\s*[\"']?([A-Za-z0-9+/_.=-]{20,})")


def entropy(value: str) -> float:
    if not value: return 0.0
    counts = Counter(value); length = len(value); return -sum((count / length) * math.log2(count / length) for count in counts.values())


def secret_fingerprint(rule: str, path: str, line: int, value: str) -> str:
    return hashlib.sha256(f"{rule}\0{path}\0{line}\0{value}".encode()).hexdigest()[:24]


def redact_line(line: str, start: int, end: int) -> str: return (line[:start] + "<redacted>" + line[end:]).strip()[:240]


def iter_text_files(project: Path, paths: Iterable[str]) -> Iterable[Path]:
    seen: set[Path] = set()
    for relative in paths:
        target = project / relative; candidates = [target] if target.is_file() else [path for path in target.rglob("*") if path.is_file()] if target.is_dir() else []
        for path in candidates:
            if path in seen or path.stat().st_size > 2_000_000: continue
            try: path.resolve().relative_to(project.resolve())
            except ValueError as exc: raise WorkspaceError(f"Secret scan path escapes the project: {path}") from exc
            seen.add(path)
            try: path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError): continue
            yield path


def allowlisted(policy: dict[str, Any], rule: str, path: str, fingerprint_value: str) -> bool:
    return any(isinstance(item, dict) and item.get("rationale") and item.get("rule") == rule and item.get("path") == path and item.get("fingerprint") == fingerprint_value for item in policy.get("secrets", {}).get("allowlist", []))


def scan_secrets(project: Path, custom_paths: Optional[list[str]] = None) -> dict[str, Any]:
    result = envelope("scan-secrets"); policy = read_json(project / POLICY_PATH); paths = custom_paths or policy.get("secrets", {}).get("paths", ["AGENTS.md", "MEMORY.md", "openspec", ".agents", ".agent-workspace"]); matches = []
    for relative in paths:
        normalized = normalize_pattern(relative)
        if has_glob(normalized) or normalized.split("/", 1)[0] not in SERVICE_PATHS:
            raise WorkspaceError(f"Secret scan is restricted to local agent workspace paths: {relative}")
    for path in iter_text_files(project, paths):
        relative = str(path.relative_to(project)).replace("\\", "/")
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            candidates = []
            for rule, pattern in SECRET_RULES:
                for match in pattern.finditer(line): candidates.append((rule, match, match.group(0)))
            for match in GENERIC_SECRET.finditer(line):
                secret = match.group(2); lowered = secret.lower()
                already_classified = any(item[2] == secret for item in candidates)
                if not already_classified and not any(marker in lowered for marker in ("example", "placeholder", "redacted", "changeme", "your_", "dummy")) and entropy(secret) >= 3.5: candidates.append(("generic-high-entropy-secret", match, secret))
            for rule, match, secret in candidates:
                fingerprint_value = secret_fingerprint(rule, relative, line_number, secret)
                if allowlisted(policy, rule, relative, fingerprint_value): continue
                secret_start = line.find(secret, match.start(), match.end()); matches.append({"rule": rule, "path": relative, "line": line_number, "fingerprint": fingerprint_value, "preview": redact_line(line, secret_start, secret_start + len(secret))})
    if matches: finding(result, "blocking", "secrets_detected", f"Detected {len(matches)} potential secret(s).", matches=matches)
    result["data"] = {"scanned_paths": paths, "findings_count": len(matches), "git_history_scanned": False}; return result


MARKDOWN_LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def validate_markdown_links(project: Path, path: Path) -> list[str]:
    broken = []
    for target in MARKDOWN_LINK.findall(path.read_text(encoding="utf-8", errors="ignore")):
        cleaned = target.strip().strip("<>").split("#", 1)[0]
        if not cleaned or re.match(r"^[a-z]+://", cleaned) or cleaned.startswith("mailto:"): continue
        resolved = (path.parent / cleaned).resolve()
        try: resolved.relative_to(project.resolve())
        except ValueError: broken.append(target); continue
        if not resolved.exists(): broken.append(target)
    return broken


def validate_markdown_structure(path: Path, required_headings: Iterable[str]) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="ignore"); return [heading for heading in required_headings if heading not in text]


def validate_completed_task(task: Any) -> list[str]:
    if not isinstance(task, dict): return ["completed task must be a JSON object"]
    errors = []
    if task.get("status") != "completed": errors.append("status must be completed")
    if task.get("outcome") not in OUTCOMES: errors.append(f"outcome must be one of {sorted(OUTCOMES)}")
    try: parse_timestamp(task.get("completed_at"))
    except WorkspaceError: errors.append("completed_at must be an ISO timestamp")
    history = task.get("state_history")
    final_entry = history[-1] if isinstance(history, list) and history and isinstance(history[-1], dict) else None
    previous_entry = history[-2] if isinstance(history, list) and len(history) >= 2 and isinstance(history[-2], dict) else None
    if not isinstance(history, list) or len(history) < 2 or final_entry is None or final_entry.get("status") != "completed": errors.append("state_history must end with completed")
    else:
        active_copy = dict(task); active_copy["state_history"] = history[:-1]; active_copy["status"] = previous_entry.get("status") if previous_entry else None
        errors.extend(validate_task(active_copy))
        try: parse_timestamp(final_entry.get("at"))
        except WorkspaceError: errors.append("completed transition must have an ISO timestamp")
    if task.get("outcome") == "accepted":
        if not task.get("acceptance_criteria") or not task.get("evidence"): errors.append("accepted task requires acceptance criteria and evidence")
        if previous_entry is None or previous_entry.get("status") != "accepted": errors.append("accepted task must transition from accepted to completed")
    return errors


def validate_workspace(project: Path) -> dict[str, Any]:
    result = envelope("validate"); policy_path = project / POLICY_PATH; policy = None
    if not policy_path.exists(): finding(result, "blocking", "missing_policy", f"Missing {POLICY_PATH}.")
    else:
        policy = read_json(policy_path)
        for error in validate_policy(policy): finding(result, "blocking", "invalid_policy", error, path=str(POLICY_PATH))
    valid_ignore, missing_patterns = gitignore_has_required_patterns(project)
    if not valid_ignore: finding(result, "blocking", "missing_gitignore_rules", "Required local workspace ignore rules are missing.", patterns=missing_patterns)
    tracked = tracked_service_files(project)
    if tracked: finding(result, "blocking", "tracked_service_files", "Local agent workspace files are tracked by Git.", paths=tracked)
    ignored_missing = existing_service_paths_are_ignored(project)
    if ignored_missing: finding(result, "blocking", "service_files_not_ignored", "Existing service paths are not ignored by Git.", paths=ignored_missing)
    for required in (Path("AGENTS.md"), Path("MEMORY.md"), WORKSPACE_DIR):
        if not (project / required).exists(): finding(result, "blocking", "missing_workspace_path", f"Missing required workspace path: {required}")
    for path in sorted((project / ACTIVE_DIR).glob("*.json")) if (project / ACTIVE_DIR).exists() else []:
        try:
            for error in validate_task(read_json(path)): finding(result, "blocking", "invalid_active_task", error, path=str(path.relative_to(project)))
        except WorkspaceError as exc: finding(result, "blocking", "invalid_active_task_json", str(exc), path=str(path.relative_to(project)))
    for path in sorted((project / RAW_DIR).glob("*/*.json")) if (project / RAW_DIR).exists() else []:
        try:
            for error in validate_completed_task(read_json(path)): finding(result, "blocking", "invalid_completed_task", error, path=str(path.relative_to(project)))
        except WorkspaceError as exc: finding(result, "blocking", "invalid_completed_task_json", str(exc), path=str(path.relative_to(project)))
    structures = ((project / RECORDS_DIR, ("# Completed task:", "## Acceptance evidence", "## Residual risks and follow-ups"), "completed"), (project / DECISIONS_DIR, ("# Decision:", "## Context", "## Decision", "## Consequences"), "decision"), (project / VERIFICATIONS_DIR, ("# Verification:", "## Verdict", "## Requirement-to-evidence"), "verification"))
    for directory, headings, kind in structures:
        for path in sorted(directory.rglob("*.md")) if directory.exists() else []:
            missing = validate_markdown_structure(path, headings)
            if missing: finding(result, "blocking", f"invalid_{kind}_record", "Required headings are missing.", path=str(path.relative_to(project)), headings=missing)
    markdown_files = []
    for root in (project / "AGENTS.md", project / "MEMORY.md", project / "openspec", project / WORKSPACE_DIR):
        if root.is_file() and root.suffix.lower() == ".md": markdown_files.append(root)
        elif root.is_dir(): markdown_files.extend(path for path in root.rglob("*.md") if path.is_file())
    for path in markdown_files:
        broken = validate_markdown_links(project, path)
        if broken: finding(result, "blocking", "broken_local_links", "Markdown contains broken local links.", path=str(path.relative_to(project)), targets=broken)
    openspec_dir = project / "openspec"
    if openspec_dir.exists():
        executable = shutil.which("openspec")
        if executable is None: finding(result, "blocking", "missing_openspec_cli", "OpenSpec exists but its CLI is unavailable.")
        else:
            for command in ([executable, "validate", "--all", "--strict", "--json"], [executable, "validate", "--archived"]):
                completed = run_command(command, project)
                if completed.returncode != 0: finding(result, "blocking", "openspec_validation_failed", completed.stderr.strip() or completed.stdout.strip() or "OpenSpec validation failed.", command=command[1:])
    else: finding(result, "info", "openspec_skipped", "OpenSpec directory is absent; OpenSpec validation was skipped.")
    result["data"] = {"policy_valid": policy is not None and not validate_policy(policy), "active_tasks_checked": len(list((project / ACTIVE_DIR).glob("*.json"))) if (project / ACTIVE_DIR).exists() else 0, "local_only": True}; return result
