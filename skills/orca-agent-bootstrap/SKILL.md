---
name: orca-agent-bootstrap
description: Prepare an existing or new software project for supervised multi-agent work in Orca by establishing the coordinator/worker contract, OpenSpec planning, AGENTS.md, durable project memory, and a file-backed active/completed task ledger. Use when onboarding a repository to Orca, repairing missing agent context, or standardizing how background workers receive and report work. Do not use merely to execute one already-prepared task.
---

# Orca Agent Bootstrap

Create a small, inspectable control plane for agents. Prefer links and compact summaries over copying the same context into several files.

## Source-of-truth boundaries

- `openspec/specs/` describes current product behavior; `openspec/changes/<change>/` describes a proposed change.
- `AGENTS.md` contains repository instructions, commands, boundaries, and the coordinator/worker contract.
- `MEMORY.md` contains only stable, verified project facts and links. Keep it short.
- `docs/agent-memory/active/` contains volatile execution state, one file per active task.
- `docs/agent-memory/completed/` contains compact completion records and evidence.
- `docs/agent-memory/decisions/` contains durable decisions and rationale.

Do not duplicate an OpenSpec proposal or long terminal output in memory. Link to it and record only execution facts, decisions, blockers, and evidence.

## Bootstrap workflow

1. Inspect the repository before writing:
   - Read any existing `AGENTS.md`, `MEMORY.md`, agent rules, OpenSpec files, contributor docs, manifests, CI configuration, and test commands.
   - Check working-tree status and preserve unrelated user changes.
   - Infer the project map, build/test/lint commands, generated paths, sensitive areas, and ownership boundaries from evidence.
2. Preview the deterministic scaffold:

   ```bash
   python3 <skill-dir>/scripts/bootstrap_project.py --project <repo-root> --dry-run
   ```

3. Run the scaffold after reviewing the preview. It creates missing files only and never overwrites existing files:

   ```bash
   python3 <skill-dir>/scripts/bootstrap_project.py --project <repo-root>
   ```

4. Merge project-specific facts into existing or newly created files. Replace every bracketed bootstrap prompt with verified information; remove sections that do not apply. Never replace an existing instruction file wholesale.
5. If OpenSpec is absent, prefer the installed official CLI:

   ```bash
   python3 <skill-dir>/scripts/bootstrap_project.py \
     --project <repo-root> \
     --init-openspec \
     --openspec-tools agents
   ```

   This intentionally does not install OpenSpec. If the command is unavailable, report the missing dependency and ask before any networked installation. If OpenSpec already exists, inspect and preserve its configuration.
6. Validate the result with read-only checks: links resolve, commands are real, no placeholder facts are presented as true, and the new files are visible in version control.
7. Report files created, files preserved, facts still needing human confirmation, and the exact next action for the first change.

For project memory rules and record lifecycle, read [references/memory-model.md](references/memory-model.md). For OpenSpec initialization or task mapping, read [references/openspec-integration.md](references/openspec-integration.md).

## Coordinator and worker workflow

When the prepared project is used for implementation:

1. The coordinator reads `AGENTS.md`, `MEMORY.md`, relevant specs, and active task records. It explores ambiguity and creates or updates an OpenSpec change before implementation.
2. The coordinator turns cohesive groups from `tasks.md` into supervised Orca Tasks. Each worker specification must state:
   - objective and OpenSpec change;
   - in-scope and forbidden files;
   - constraints and dependencies;
   - acceptance criteria;
   - required verification and evidence;
   - expected memory updates;
   - selected Orca agent/harness and optional model/effort, with a short routing reason.
3. Use the official Orca `orchestration` skill for runtime operations. Load its version-matched live guide before mutating orchestration state. The coordinator plans, dispatches, answers worker questions, and verifies; workers implement only their assigned scope. The coordinator's own agent does not constrain worker selection: a Codex coordinator may dispatch Cursor, Antigravity, Claude, OpenCode, or any other agent ID enabled on the target Orca server.
4. Put concurrent writers in separate child worktrees. Do not dispatch tasks that knowingly edit the same files in parallel unless the coordinator defines an integration order.
5. Create `docs/agent-memory/active/<task-key>.md` when work is dispatched. Correlate the OpenSpec change name, Orca Task ID, Dispatch ID, and worktree.
6. After starting independent workers, let Orca wake the coordinator. Do not busy-poll. Send follow-up guidance through orchestration messaging rather than typing into a worker terminal.
7. A `worker_done` message is a claim, not proof. The coordinator reviews the diff, runs or inspects required checks, compares behavior with OpenSpec, and either requests focused rework or accepts the result.
8. On acceptance, check off supported OpenSpec tasks, move the active record into `completed/`, add or update decision records, and compact `MEMORY.md` only when stable project knowledge changed.
9. Archive the OpenSpec change only after all requirements are implemented and verified. Destructive cleanup, merging, pushing, or publishing still requires the user's ordinary authorization.

Read [references/orchestration-contract.md](references/orchestration-contract.md) when configuring roles, task contracts, verification, retries, or background execution.

## Quality gates

- Planning and execution state must remain distinguishable: OpenSpec is intent; Orca is live assignment state; agent memory is rationale and evidence.
- Every active task has one owner and one next action.
- Every completed task cites observable evidence, not only an agent summary.
- Agent routing is capability-based and recorded. Do not assume that coordinator and worker share a provider, model, authentication, context limits, or supported effort levels.
- Stable memory contains no secrets, credentials, raw logs, speculative facts, or transient progress.
- When facts conflict, prefer executable code and verified behavior, then current specs, then memory. Record and resolve the mismatch instead of silently choosing.
- Stop and ask the user when bootstrap would overwrite material instructions, select between incompatible architectures, or install external software.

For optional hardening such as independent review, model routing, context budgets, CI checks, and recovery policies, read [references/extensions.md](references/extensions.md).
