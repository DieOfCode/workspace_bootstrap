# Agent instructions for {{PROJECT_NAME}}

## Mission

Preserve user intent and verified behavior. For planned changes, OpenSpec defines the requested outcome; this file defines how agents work in the repository.

## Read before acting

1. Read this file and the nearest nested `AGENTS.md`, if any.
2. Read `MEMORY.md` for stable project context.
3. For change work, read the relevant `openspec/changes/<change>/` artifacts.
4. For delegated work, read the matching `docs/agent-memory/active/<task-key>.md`.

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

Do not invent commands. If a canonical command is unknown, inspect CI and project manifests or report the gap.

## Coordinator contract

- The coordinator owns discovery, OpenSpec artifacts, decomposition, dependency ordering, worker questions, and acceptance.
- Turn cohesive OpenSpec task groups into self-contained Orca Tasks with scope, constraints, acceptance criteria, and verification.
- Choose workers from any Orca agent IDs enabled on the target server. The coordinator's own CLI/provider is not a routing restriction; select agent, optional model, and effort by capability, risk, host compatibility, latency, and cost.
- Record requested and effective worker routing in the active task record. Do not silently substitute a user-requested agent or model.
- Use separate child worktrees for concurrent writers.
- Treat `worker_done` as a completion claim. Review the diff and evidence before accepting it.
- Update stable memory only when project-wide truth changed.

## Worker contract

- Implement only the assigned task and file scope.
- Follow the task contract regardless of whether the coordinator uses a different agent CLI, provider, or model family.
- Preserve unrelated user changes and existing public contracts.
- Ask the coordinator when requirements conflict or scope must expand.
- Run the assigned checks and report exact outcomes, changed files, residual risks, and follow-ups.
- Keep the active task record current at meaningful transitions.
- Do not archive OpenSpec changes, merge, push, publish, or rewrite project-wide instructions unless explicitly assigned and authorized.

## Definition of done

- Acceptance criteria are satisfied with observable evidence.
- Relevant tests and static checks pass, or failures are explained and accepted.
- OpenSpec tasks reflect verified completion.
- Active memory is compacted into completed memory.
- Durable decisions and stable project facts are recorded without duplicating specifications or logs.

## Repository guardrails

- [fill sensitive paths, generated-code policy, compatibility requirements, or state none]
- Never store credentials or production data in specifications, prompts, logs, or agent memory.
