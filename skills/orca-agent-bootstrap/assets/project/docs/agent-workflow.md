# Agent workflow

## Roles

- **Coordinator:** plans with OpenSpec, decomposes work, dispatches Orca Tasks, resolves questions, and accepts evidence.
- **Executor:** implements one bounded task in its assigned worktree and reports evidence.
- **Verifier:** independently checks risky or cross-cutting work when assigned.

## Lifecycle

1. Explore the request and inspect current behavior.
2. Create or revise an OpenSpec proposal, delta specs, design, and task list.
3. Review the plan before implementation when scope or architecture is material.
4. Create an active memory record for each dispatched task.
5. Run non-conflicting tasks in separate worktrees.
6. Let Orca notify the coordinator of questions, failures, and completion.
7. Verify diffs and checks against OpenSpec.
8. Rework or accept; then compact the task record and capture durable decisions.
9. Archive the OpenSpec change after the complete change is verified.

## Truth ownership

| Concern | Source |
|---|---|
| Current intended behavior | `openspec/specs/` |
| Proposed behavior | `openspec/changes/<change>/` |
| Repository rules | `AGENTS.md` |
| Stable project context | `MEMORY.md` |
| Live task state | `docs/agent-memory/active/` and Orca |
| Finished work and evidence | `docs/agent-memory/completed/` |
| Decision rationale | `docs/agent-memory/decisions/` |

## Completion gate

A task is complete only when the coordinator can point to the relevant requirement, the implementation diff, and verification evidence. An agent summary alone is insufficient.
