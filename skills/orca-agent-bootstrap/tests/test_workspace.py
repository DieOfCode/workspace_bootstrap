from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import mock


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import workspace  # noqa: E402
import workspace_lib as lib  # noqa: E402


def git(project: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=project, text=True, capture_output=True, check=False)


class WorkspaceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.project = Path(self.temporary.name)
        self.templates = SKILL_ROOT / "assets" / "project"

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def bootstrap(self, git_repo: bool = False) -> dict:
        if git_repo:
            self.assertEqual(git(self.project, "init", "-b", "main").returncode, 0)
            git(self.project, "config", "user.email", "test@example.invalid")
            git(self.project, "config", "user.name", "Test")
            (self.project / "README.md").write_text("# Fixture\n", encoding="utf-8")
            git(self.project, "add", "README.md")
            self.assertEqual(git(self.project, "commit", "-m", "fixture").returncode, 0)
        return lib.bootstrap(self.project, self.templates)

    def task(self, key: str, writes: list[str], **overrides) -> dict:
        template = (self.templates / ".agent-workspace/templates/active-task.json").read_text()
        task = json.loads(lib.render_template(template, "Fixture"))
        task["task_key"] = key
        task["scope"]["write"] = writes
        for name, value in overrides.items():
            task[name] = value
        return task

    def write_task(self, task: dict) -> Path:
        path = self.project / lib.ACTIVE_DIR / f"{task['task_key']}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        lib.atomic_write_json(path, task)
        return path

    def test_bootstrap_is_local_idempotent_and_only_gitignore_is_visible(self) -> None:
        first = self.bootstrap(git_repo=True)
        self.assertTrue(first["ok"])
        expected = set(lib.IGNORE_PATTERNS)
        actual = set(lib.parse_gitignore_lines((self.project / ".gitignore").read_text()))
        self.assertTrue(expected.issubset(actual))
        second = lib.bootstrap(self.project, self.templates)
        self.assertTrue(second["ok"])
        text = (self.project / ".gitignore").read_text()
        self.assertEqual(text.count(lib.IGNORE_BEGIN), 1)
        status = git(self.project, "status", "--short").stdout.splitlines()
        self.assertEqual(status, ["?? .gitignore"])

    def test_bootstrap_refuses_to_untrack_existing_agent_files(self) -> None:
        self.assertEqual(git(self.project, "init", "-b", "main").returncode, 0)
        git(self.project, "config", "user.email", "test@example.invalid")
        git(self.project, "config", "user.name", "Test")
        (self.project / "AGENTS.md").write_text("tracked\n")
        git(self.project, "add", "AGENTS.md")
        git(self.project, "commit", "-m", "tracked agent file")
        result = lib.bootstrap(self.project, self.templates)
        self.assertFalse(result["ok"])
        self.assertEqual(result["findings"][0]["code"], "tracked_service_files")
        self.assertFalse((self.project / ".agent-workspace").exists())
        self.assertEqual((self.project / "AGENTS.md").read_text(), "tracked\n")

    def test_bootstrap_migrates_missing_planning_policy_without_rewriting_instructions(self) -> None:
        self.bootstrap()
        policy_path = self.project / lib.POLICY_PATH
        policy = lib.read_json(policy_path)
        policy.pop("planning")
        lib.atomic_write_json(policy_path, policy)
        agents = self.project / "AGENTS.md"
        agents.write_text(agents.read_text() + "\nCustom local instruction.\n")

        result = lib.bootstrap(self.project, self.templates)

        self.assertTrue(result["ok"])
        self.assertEqual(lib.read_json(policy_path)["planning"], lib.PLANNING_POLICY_DEFAULTS)
        self.assertIn("Custom local instruction.", agents.read_text())
        self.assertIn("migrate", {change["action"] for change in result["changes"]})

    def test_bootstrap_installs_local_agents_openspec_skills(self) -> None:
        commands = []

        def fake_run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
            commands.append(command)
            return subprocess.CompletedProcess(command, 0, "initialized", "")

        with mock.patch.object(lib.shutil, "which", return_value="/usr/local/bin/openspec"), mock.patch.object(lib, "run_openspec_command", side_effect=fake_run):
            result = lib.bootstrap(self.project, self.templates, init_openspec=True)
        self.assertTrue(result["ok"])
        self.assertEqual(commands, [["/usr/local/bin/openspec", "init", str(self.project.resolve()), "--tools", "agents", "--profile", "core", "--no-animation", "--no-copilot-cloud"]])

        blocked = lib.bootstrap(self.project, self.templates, init_openspec=True, openspec_tools="cursor")
        self.assertFalse(blocked["ok"])
        self.assertEqual(blocked["findings"][0]["code"], "nonlocal_openspec_tools")

    def test_managed_openspec_commands_use_local_config_and_disable_telemetry(self) -> None:
        completed = subprocess.CompletedProcess(["openspec", "--version"], 0, "1.16.0", "")
        with mock.patch.object(lib.subprocess, "run", return_value=completed) as run:
            result = lib.run_openspec_command(["openspec", "--version"], self.project)
        self.assertEqual(result.returncode, 0)
        environment = run.call_args.kwargs["env"]
        self.assertEqual(environment["OPENSPEC_TELEMETRY"], "0")
        self.assertEqual(environment["XDG_CONFIG_HOME"], str((self.project / lib.OPENSPEC_CONFIG_DIR).resolve()))

    def test_doctor_detects_supported_stacks(self) -> None:
        fixtures = {
            "node": {
                "package.json": json.dumps({"scripts": {"build": "vite build", "test": "vitest", "lint": "eslint ."}}),
                "package-lock.json": "{}",
            },
            "python": {"pyproject.toml": "[tool.pytest.ini_options]\n[tool.ruff]\n"},
            "flutter": {"pubspec.yaml": "dependencies:\n  flutter:\n    sdk: flutter\n"},
            "monorepo": {"package.json": json.dumps({"scripts": {"test": "test"}}), "go.mod": "module fixture\n"},
        }
        for expected, files in fixtures.items():
            with self.subTest(expected=expected), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                for name, content in files.items():
                    (root / name).write_text(content)
                detected = lib.detect_project(root)
                self.assertNotIn("ci", detected)
                names = {item["name"] for item in detected["stacks"]}
                if expected == "monorepo":
                    self.assertTrue({"node", "go"}.issubset(names))
                else:
                    self.assertIn(expected, names)

    def test_doctor_apply_preserves_custom_text_and_updates_placeholders(self) -> None:
        self.bootstrap()
        (self.project / "package.json").write_text(json.dumps({"scripts": {"build": "vite build", "test": "vitest"}}))
        agents = self.project / "AGENTS.md"
        agents.write_text(agents.read_text() + "\nCustom rule: preserve me.\n")
        result = lib.doctor(self.project, apply=True)
        self.assertTrue(result["ok"])
        text = agents.read_text()
        self.assertIn("Custom rule: preserve me.", text)
        self.assertIn("`npm run build`", text)
        policy = lib.read_json(self.project / lib.POLICY_PATH)
        self.assertEqual(policy["project"]["stacks"][0]["name"], "node")

    def test_risk_recommends_but_does_not_request_verifier(self) -> None:
        self.bootstrap()
        task = self.task("auth-change", ["src/auth.py"])
        task["acceptance_criteria"] = ["Authorization blocks invalid users"]
        path = self.write_task(task)
        result = lib.risk(self.project, path, apply=True)
        self.assertEqual(result["data"]["level"], "high")
        self.assertTrue(result["data"]["verifier_recommended"])
        self.assertFalse(result["data"]["verifier_requested"])
        updated = lib.read_json(path)
        self.assertEqual(updated["routing"]["profile"], "executor-complex")
        self.assertFalse(updated["verifier_requested"])

        coordinator = self.task("plan-work", ["openspec/changes/example/tasks.md"], task_type="coordinator")
        self.assertEqual(lib.assess_risk(coordinator)["routing_profile"], "coordinator")
        specialist = self.task("database-work", ["db/schema.sql"], task_type="specialist")
        self.assertEqual(lib.assess_risk(specialist)["routing_profile"], "specialist")
        low = self.task("small-edit", ["src/copy.py"])
        self.assertEqual(lib.assess_risk(low)["routing_profile"], "executor-standard")

    def test_conflicts_definite_potential_and_none(self) -> None:
        self.bootstrap()
        (self.project / "src").mkdir()
        (self.project / "src/app.py").write_text("pass\n")
        existing = self.task("existing", ["src/app.py"])
        existing["orca"]["worktree"] = "/tmp/existing-worktree"
        self.write_task(existing)

        definite = self.task("candidate-exact", ["src/app.py"])
        exact_path = self.project / "candidate-exact.json"
        lib.atomic_write_json(exact_path, definite)
        result = lib.conflicts(self.project, exact_path)
        self.assertFalse(result["ok"])
        self.assertEqual(result["data"]["recommended_dependencies"], ["existing"])

        potential = self.task("candidate-glob", ["src/**/*.py"])
        potential_path = self.project / "candidate-glob.json"
        lib.atomic_write_json(potential_path, potential)
        (self.project / "src/app.py").unlink()
        result = lib.conflicts(self.project, potential_path)
        self.assertTrue(result["ok"])
        self.assertTrue(result["data"]["potential"])

        clean = self.task("candidate-docs", ["docs/*.md"])
        clean_path = self.project / "candidate-docs.json"
        lib.atomic_write_json(clean_path, clean)
        result = lib.conflicts(self.project, clean_path)
        self.assertFalse(result["ok"])
        self.assertTrue(result["data"]["worktree_violations"])
        clean["orca"]["worktree"] = "/tmp/docs-worktree"
        lib.atomic_write_json(clean_path, clean)
        result = lib.conflicts(self.project, clean_path)
        self.assertTrue(result["ok"])
        self.assertFalse(result["data"]["definite"])

    def test_complete_and_compact_preserve_raw_records(self) -> None:
        self.bootstrap()
        task = self.task("finished-task", ["src/app.py"])
        task["acceptance_criteria"] = ["Test passes"]
        task["evidence"] = ["python -m unittest: passed"]
        task["result_summary"] = "Implemented the requested behavior."
        task["openspec"] = {"change": "finish-feature", "task": "1.1", "verified_task": None, "verified_at": None}
        task["status"] = "accepted"
        task["state_history"].extend([
            {"status": "dispatched", "at": "2025-12-01T00:00:00Z"},
            {"status": "verifying", "at": "2025-12-15T00:00:00Z"},
            {"status": "accepted", "at": "2025-12-31T00:00:00Z"},
        ])
        path = self.write_task(task)
        completed_at = "2026-01-01T00:00:00Z"
        apply_state = {
            "progress": {"total": 1, "complete": 1, "remaining": 0},
            "tasks": [{"id": "1", "description": "1.1 Test passes", "done": True, "sourcePath": str(self.project / "openspec/changes/finish-feature/tasks.md"), "line": 5}],
        }
        validation = {"summary": {"totals": {"items": 1, "passed": 1, "failed": 0}}}
        with mock.patch.object(lib, "openspec_apply_state", return_value=apply_state), mock.patch.object(lib, "validate_openspec_change", return_value=(True, "", validation)):
            result = lib.complete(self.project, path, "accepted", completed_at)
        self.assertTrue(result["ok"])
        self.assertEqual(result["data"]["openspec"]["task"]["id"], "1")
        self.assertFalse(path.exists())
        raw = self.project / lib.RAW_DIR / "2026-01/finished-task.json"
        record = self.project / lib.RECORDS_DIR / "2026-01/finished-task.md"
        self.assertTrue(raw.exists())
        self.assertTrue(record.exists())
        result = lib.compact(self.project, "2026-02-15T00:00:00Z")
        self.assertTrue(result["ok"])
        rollup = self.project / lib.ROLLUPS_DIR / "2026-01.md"
        self.assertTrue(rollup.exists())
        before = rollup.read_text()
        result = lib.compact(self.project, "2026-02-15T00:00:00Z")
        self.assertEqual(before, rollup.read_text())
        result = lib.compact(self.project)
        self.assertEqual(before, rollup.read_text())
        self.assertTrue(raw.exists())

    def test_complete_rejects_unchecked_openspec_task(self) -> None:
        self.bootstrap()
        task = self.task("unfinished-task", ["src/app.py"])
        task["acceptance_criteria"] = ["Test passes"]
        task["evidence"] = ["python -m unittest: passed"]
        task["openspec"] = {"change": "finish-feature", "task": "1.1", "verified_task": None, "verified_at": None}
        task["status"] = "accepted"
        task["state_history"].extend([
            {"status": "dispatched", "at": "2025-12-01T00:00:00Z"},
            {"status": "verifying", "at": "2025-12-15T00:00:00Z"},
            {"status": "accepted", "at": "2025-12-31T00:00:00Z"},
        ])
        path = self.write_task(task)
        apply_state = {"progress": {"total": 1, "complete": 0, "remaining": 1}, "tasks": [{"id": "1", "description": "1.1 Test passes", "done": False}]}
        with mock.patch.object(lib, "openspec_apply_state", return_value=apply_state):
            result = lib.complete(self.project, path, "accepted", "2026-01-01T00:00:00Z")
        self.assertFalse(result["ok"])
        self.assertEqual(result["findings"][0]["code"], "openspec_task_incomplete")
        self.assertTrue(path.exists())

    def test_validate_rejects_invalid_state_transition(self) -> None:
        self.bootstrap()
        task = self.task("bad-transition", ["src/app.py"])
        task["status"] = "accepted"
        task["state_history"].append({"status": "accepted", "at": "2026-01-01T00:00:00Z"})
        self.write_task(task)
        result = lib.validate_workspace(self.project)
        self.assertFalse(result["ok"])
        messages = [item["message"] for item in result["findings"] if item["code"] == "invalid_active_task"]
        self.assertTrue(any("ready -> accepted" in message for message in messages))

    def test_secret_scan_redacts_and_honors_exact_allowlist(self) -> None:
        self.bootstrap()
        secret = "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ123456"
        (self.project / "MEMORY.md").write_text(f"token = {secret}\n")
        result = lib.scan_secrets(self.project)
        self.assertFalse(result["ok"])
        serialized = json.dumps(result)
        self.assertNotIn(secret, serialized)
        match = result["findings"][0]["matches"][0]
        policy = lib.read_json(self.project / lib.POLICY_PATH)
        policy["secrets"]["allowlist"] = [{
            "rule": match["rule"],
            "path": match["path"],
            "fingerprint": match["fingerprint"],
            "rationale": "Fixture token used for scanner testing",
        }]
        lib.atomic_write_json(self.project / lib.POLICY_PATH, policy)
        self.assertTrue(lib.scan_secrets(self.project)["ok"])

    def test_validate_rejects_tracked_local_files(self) -> None:
        self.bootstrap(git_repo=True)
        clean = lib.validate_workspace(self.project)
        self.assertTrue(clean["ok"])
        self.assertEqual(git(self.project, "add", "-f", "AGENTS.md").returncode, 0)
        blocked = lib.validate_workspace(self.project)
        self.assertFalse(blocked["ok"])
        self.assertIn("tracked_service_files", {item["code"] for item in blocked["findings"]})

    def test_validate_requires_openspec_cli_when_local_openspec_exists(self) -> None:
        self.bootstrap()
        (self.project / "openspec").mkdir()
        with mock.patch.object(lib.shutil, "which", return_value=None):
            result = lib.validate_workspace(self.project)
        self.assertFalse(result["ok"])
        self.assertIn("missing_openspec_cli", {item["code"] for item in result["findings"]})

    def test_cli_json_envelope_and_exit_codes(self) -> None:
        output = StringIO()
        with redirect_stdout(output):
            code = workspace.main(["bootstrap", "--project", str(self.project), "--json"])
        result = json.loads(output.getvalue())
        self.assertEqual(code, 0)
        self.assertEqual(set(("schema_version", "command", "ok", "findings", "changes", "data")), set(result))

        secret = "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ123456"
        (self.project / "MEMORY.md").write_text(f"token = {secret}\n")
        output = StringIO()
        with redirect_stdout(output):
            code = workspace.main(["scan-secrets", "--project", str(self.project), "--json"])
        self.assertEqual(code, 2)
        self.assertNotIn(secret, output.getvalue())

        output = StringIO()
        with redirect_stdout(output):
            code = workspace.main(["risk", "--project", str(self.project), "--task", str(self.project / "missing.json"), "--json"])
        self.assertEqual(code, 1)

        output = StringIO()
        with redirect_stdout(output):
            code = workspace.main(["risk", "--project", str(self.project), "--json"])
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(output.getvalue())["command"], "risk")

        output = StringIO()
        with redirect_stdout(output):
            code = workspace.main(["scan-secrets", "--project", str(self.project), "--paths", "src", "--json"])
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
