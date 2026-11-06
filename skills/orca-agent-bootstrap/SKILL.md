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

4. To initialize local OpenSpec and its standard workflow skills, add `--init-openspec`. Local-only mode uses `--tools agents`, which writes the generated skills only under ignored `.agents/`.
5. Discover project facts in report mode, then explicitly apply verified detections:

   ```bash
   python3 <skill-dir>/scripts/workspace.py doctor --project <repo-root> --json
   python3 <skill-dir>/scripts/workspace.py doctor --project <repo-root> --apply --json
   ```

6. Run local validation and secret scanning. Report created/preserved files, unresolved findings, and the first OpenSpec action.

The legacy `scripts/bootstrap_project.py` remains a compatible wrapper. Read [references/extensions.md](references/extensions.md) for command behavior and [references/openspec-integration.md](references/openspec-integration.md) before initializing or validating OpenSpec.

## Orchestrated work

1. Treat OpenSpec as the only source of truth for the change plan. Use the generated `openspec-explore` and `openspec-propose` skills to create or refine proposal, specs, design, and tasks. Do not copy that plan into `MEMORY.md` or `.agent-workspace`.
2. Read the executable task list with `openspec instructions apply --change <change> --json`. Create one `.agent-workspace/memory/active/<task-key>.json` per planned worker and record the exact OpenSpec change and task ID. Runtime records contain ownership, routing, scope, blockers, and evidence—not the product plan.
3. Before dispatch, run:

   ```bash
   python3 <skill-dir>/scripts/workspace.py risk --project <repo-root> --task <task-json> --apply --json
   python3 <skill-dir>/scripts/workspace.py conflicts --project <repo-root> --candidate <task-json> --json
   ```

4. Definite write overlap blocks parallel dispatch and becomes a sequential dependency. Potential glob overlap is a warning that requires scope refinement. Separate worktrees do not make overlapping writes independent.
5. Select any enabled Orca agent/model matching the capability profile. The coordinator's provider is not a worker allow-list. Do not silently substitute an explicit user choice.
6. High-risk work recommends an independent verifier but never starts one automatically. A verifier requires an explicit user or coordinator decision, fresh context, and read-only scope by default.
7. Treat `worker_done` as a claim. Verify the diff and evidence against OpenSpec before acceptance. Only then check the corresponding task in OpenSpec `tasks.md`.
8. Run `workspace.py complete` after the task checkbox is checked. For an accepted outcome it refuses completion unless the referenced OpenSpec task is done and the change passes strict OpenSpec validation. The operational record links to OpenSpec and does not duplicate its proposal, specs, design, or task text.
9. After every task is accepted, validate the whole change. Use `openspec-sync-specs` only when main specs must be updated before archive; otherwise use `openspec-archive-change`, which owns final plan history. Archive requires an explicit user or coordinator decision.
10. During maintenance, run `workspace.py compact`; it rolls up operational evidence after 30 days without replacing OpenSpec history. Before final reporting, run `workspace.py scan-secrets` and `workspace.py validate` locally.

Read [references/orchestration-contract.md](references/orchestration-contract.md) for worker/verifier contracts and [references/memory-model.md](references/memory-model.md) for state lifecycle.

## Quality gates

- OpenSpec is the source of truth for intent, tasks, progress, and archived change history. Orca is live assignment state; `.agent-workspace` is local runtime rationale and evidence.
- Every active task has one owner, one next action, explicit write scope, and valid JSON state.
- Accepted runtime tasks contain acceptance evidence and reference a checked OpenSpec task.
- Requested and effective agent/model/effort are recorded.
- Agent files remain ignored and absent from the Git index.
- Secret findings are redacted; exact allowlist entries require a rationale.
- Do not install external software, untrack files, archive OpenSpec, merge, push, or publish without the user's ordinary authorization.
