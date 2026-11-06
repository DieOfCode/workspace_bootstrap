---
name: orca-agent-bootstrap
description: Prepare a software project for supervised multi-agent work in Orca using a local-only ignored workspace, OpenSpec planning, stack/command discovery, structured task state, conflict checks, risk-based routing, memory rollups, validation, and secret scanning. Use when onboarding or repairing a repository's agent workflow. Do not use merely to execute one already-prepared task.
---

# Orca Agent Bootstrap

Create a local control plane for agents without committing agent instructions, specifications, memory, or runtime state.

## Local-only invariant

The target project must ignore and never track:

- `AGENTS.md` and `MEMORY.md`;
- `openspec/` and `.agents/`;
- `.agent-workspace/` including policy, reports, tasks, decisions, verifications, and rollups.

Only the managed `.gitignore` update is expected to enter the project diff. If any service path is already tracked, stop and report the exact migration command; never run `git rm --cached` without separate user authorization.

## Bootstrap

1. Inspect repository status and existing agent/OpenSpec files.
2. Preview:

   ```bash
   python3 <skill-dir>/scripts/workspace.py bootstrap --project <repo-root> --dry-run --json
   ```

3. Bootstrap after reviewing the plan:

   ```bash
   python3 <skill-dir>/scripts/workspace.py bootstrap --project <repo-root> --json
   ```

4. To initialize local OpenSpec with its installed official CLI, add `--init-openspec`. Local-only mode uses the official `--tools none`; project-local Orca guidance is installed under ignored `.agents/` instead of generating provider-specific tracked directories.
5. Discover project facts in report mode, then explicitly apply verified detections:

   ```bash
   python3 <skill-dir>/scripts/workspace.py doctor --project <repo-root> --json
   python3 <skill-dir>/scripts/workspace.py doctor --project <repo-root> --apply --json
   ```

6. Run local validation and secret scanning. Report created/preserved files, unresolved findings, and the first OpenSpec action.

The legacy `scripts/bootstrap_project.py` remains a compatible wrapper. Read [references/extensions.md](references/extensions.md) for command behavior and [references/openspec-integration.md](references/openspec-integration.md) before initializing or validating OpenSpec.

## Orchestrated work

1. The coordinator reads local `AGENTS.md`, `MEMORY.md`, OpenSpec artifacts, policy, and relevant active task JSON.
2. Create one `.agent-workspace/memory/active/<task-key>.json` per planned worker from the template. Include precise read/write/forbidden scopes, acceptance criteria, verification, dependencies, and requested routing.
3. Before dispatch, run:

   ```bash
   python3 <skill-dir>/scripts/workspace.py risk --project <repo-root> --task <task-json> --apply --json
   python3 <skill-dir>/scripts/workspace.py conflicts --project <repo-root> --candidate <task-json> --json
   ```

4. Definite write overlap blocks parallel dispatch and becomes a sequential dependency. Potential glob overlap is a warning that requires scope refinement. Separate worktrees do not make overlapping writes independent.
5. Select any enabled Orca agent/model matching the capability profile. The coordinator's provider is not a worker allow-list. Do not silently substitute an explicit user choice.
6. High-risk work recommends an independent verifier but never starts one automatically. A verifier requires an explicit user or coordinator decision, fresh context, and read-only scope by default.
7. Treat `worker_done` as a claim. Verify the diff and evidence against OpenSpec before acceptance.
8. After acceptance or closure, run `workspace.py complete`. During maintenance, run `workspace.py compact`; it creates 30-day monthly rollups and never deletes raw records.
9. Before reporting completion, run `workspace.py scan-secrets` and `workspace.py validate` locally.

Read [references/orchestration-contract.md](references/orchestration-contract.md) for worker/verifier contracts and [references/memory-model.md](references/memory-model.md) for state lifecycle.

## Quality gates

- OpenSpec is local intent; Orca is live assignment state; `.agent-workspace` is local rationale and evidence.
- Every active task has one owner, one next action, explicit write scope, and valid JSON state.
- Accepted tasks contain acceptance evidence.
- Requested and effective agent/model/effort are recorded.
- Agent files remain ignored and absent from the Git index.
- Secret findings are redacted; exact allowlist entries require a rationale.
- Do not install external software, untrack files, archive OpenSpec, merge, push, or publish without the user's ordinary authorization.
