# Agent instructions for {{PROJECT_NAME}}

## Mission

Preserve user intent and verified behavior. For planned changes, OpenSpec defines the requested outcome; this file defines how agents work in the repository.

This file and every agent/OpenSpec artifact are local-only. They must remain covered by the managed `.gitignore` block and must never be committed.

## Read before acting

1. Read this file and the nearest nested `AGENTS.md`, if any.
2. Read `MEMORY.md` for stable project context.
3. For change work, read the relevant `openspec/changes/<change>/` artifacts.
4. For delegated work, read the matching `.agent-workspace/memory/active/<task-key>.json`.

## Project map

- Application/source: [fill from repository inspection]
- Tests: [fill from repository inspection]
- Generated files: [fill or state none]
- Operational documentation: [fill from repository inspection]

## Canonical commands

- Setup: `[verified command]`
- Build: `[verified command]`
- Test: `[verified command]`
- Lint/format: `[verified command]`

Do not invent commands. If a canonical command is unknown, inspect project manifests and executable scripts or report the gap.

## Coordinator contract

- OpenSpec is the source of truth for proposal, requirements, design, task progress, and archived change history. Do not duplicate that plan in runtime memory.
- The coordinator owns discovery, OpenSpec coherence, decomposition, dependency ordering, worker questions, and acceptance.
- Read task IDs with `openspec instructions apply --change <change> --json`, then turn cohesive task groups into self-contained Orca Tasks with scope, constraints, acceptance criteria, and verification.
- Choose workers from any Orca agent IDs enabled on the target server. The coordinator's own CLI/provider is not a routing restriction; select agent, optional model, and effort by capability, risk, host compatibility, latency, and cost.
- Record requested and effective worker routing in the active task record. Do not silently substitute a user-requested agent or model.
- Run `workspace.py risk` and `workspace.py conflicts` before dispatch. Definite write overlaps become sequential dependencies.
- Use separate child worktrees for concurrent writers.
- Treat `worker_done` as a completion claim. Review the diff and evidence before accepting it.
- Launch an independent verifier only after an explicit user or coordinator decision; high risk is a recommendation, not automatic authority.
- After accepting evidence, check the corresponding OpenSpec task and run `workspace.py complete`. Accepted runtime completion requires that checked task and strict change validation.
- After all tasks are complete, use the OpenSpec sync/archive workflow explicitly; runtime records are not a substitute for OpenSpec history.
- Update stable memory only when project-wide truth changed.

## Worker contract

- Implement only the assigned task and file scope.
- Follow the task contract regardless of whether the coordinator uses a different agent CLI, provider, or model family.
- Preserve unrelated user changes and existing public contracts.
- Ask the coordinator when requirements conflict or scope must expand.
- Run the assigned checks and report exact outcomes, changed files, residual risks, and follow-ups.
- Keep the active task record current at meaningful transitions.
- Do not archive OpenSpec changes, merge, push, publish, or rewrite project-wide instructions unless explicitly assigned and authorized.
- Never add `AGENTS.md`, `MEMORY.md`, `openspec/`, `.agents/`, or `.agent-workspace/` to Git.

## Definition of done

- Acceptance criteria are satisfied with observable evidence.
- Relevant tests and static checks pass, or failures are explained and accepted.
- OpenSpec tasks reflect verified completion.
- Active memory is compacted into completed memory.
- Durable decisions and stable project facts are recorded without duplicating specifications or logs.
- `workspace.py scan-secrets` and `workspace.py validate` pass locally.

## Repository guardrails

- [fill sensitive paths, generated-code policy, compatibility requirements, or state none]
- Never store credentials or production data in specifications, prompts, logs, or agent memory.
