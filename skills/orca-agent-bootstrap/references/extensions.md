# Local workspace commands

Use the single dependency-free CLI:

```bash
python3 <skill-dir>/scripts/workspace.py <command> --project <repo-root> --json
```

Every command returns `schema_version`, `command`, `ok`, `findings`, `changes`, and `data`. Exit `0` means success or warnings, `1` means an operational/schema input error, and `2` means a blocking policy finding.

## Commands

- `bootstrap`: creates local templates, directories, and the managed `.gitignore` block. It refuses tracked service files and never untracks them.
- `doctor`: detects stacks and canonical commands. Use report mode first; `--apply` updates local policy and untouched placeholders. `--write-report` stores a timestamped local report.
- `risk --task <json>`: returns `low|medium|high`, reasons, a capability profile, and a verifier recommendation. `--apply` updates the task JSON.
- `conflicts --candidate <json>`: compares write scopes with active tasks. Definite overlap exits `2` and returns recommended sequential dependencies; potential glob overlap is a warning. Disjoint concurrent writers still require distinct non-empty worktree IDs.
- `complete --task <json> --outcome <value>`: preserves runtime JSON, writes a compact execution record, and removes the active copy only after both artifacts exist. An `accepted` outcome requires evidence, an accepted state transition, a checked referenced OpenSpec task, and strict validation of that change. It never copies or archives the OpenSpec plan.
- `compact`: creates monthly rollups for records at least 30 days old. It never prunes raw data.
- `scan-secrets`: scans only local agent/OpenSpec paths with built-in high-confidence rules and redacted output. It does not scan Git history.
- `validate`: checks schemas, records, links, local OpenSpec, `.gitignore`, and the Git index.

## Local-only paths

The managed ignore block covers `AGENTS.md`, `MEMORY.md`, `openspec/`, `.agents/`, and `.agent-workspace/`. The only expected repository diff from bootstrap is `.gitignore`.

With `--init-openspec`, bootstrap uses `openspec init --tools agents --profile core` so the standard OpenSpec workflow skills remain under ignored `.agents/`. Provider-specific tool targets are rejected by this local-only version.

## Verifier boundary

The CLI may recommend a verifier but never launches one. Creating a verifier task is an explicit coordinator or user decision. Store its report under `.agent-workspace/memory/verifications/` using the bundled template.
