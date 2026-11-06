# Orca orchestration contract

Use this reference when the project is ready and a coordinator must delegate implementation.

## Roles

### Coordinator

Use the strongest model available for ambiguity reduction, architecture, decomposition, and review. The coordinator:

- owns the OpenSpec change and task graph;
- writes self-contained worker contracts;
- chooses models and worktrees;
- answers questions and resolves conflicts;
- verifies evidence before accepting work;
- updates durable memory after decisions stabilize.

The coordinator should not implement ordinary assigned tasks. It may make a narrowly scoped repair when delegation would cost more than the change, or after a worker has failed and the coordinator records why it is taking over.

### Executor

Use a faster or cheaper model for bounded implementation. An executor:

- reads `AGENTS.md`, the assigned OpenSpec artifacts, and its active task record;
- changes only the assigned scope;
- runs the required checks;
- records discoveries and evidence without rewriting project-wide rules;
- asks the coordinator when the contract is ambiguous;
- reports completion exactly once through the active Orca dispatch.

### Verifier

For risky changes, use a fresh-context worker that did not implement the change. It checks requirements, tests, regressions, security boundaries, and unsupported claims. It does not expand scope or fix code unless explicitly assigned a follow-up Task.

## Worker task contract

Every dispatched task should include:

```markdown
# Objective
[One observable outcome]

## Context
- OpenSpec change: [name]
- Relevant requirements/design: [paths]
- Depends on: [task IDs or none]

## Scope
- May edit: [paths]
- Must not edit: [paths]
- Preserve: [interfaces/behavior]

## Acceptance criteria
- [Testable criterion]

## Verification
- Run: `[command]`
- Inspect: [observable behavior or artifact]
- Report: files changed, checks and results, residual risks

## Memory
- Update: `docs/agent-memory/active/[task-key].md`
- Propose a decision record when: [decision threshold]
```

Do not tell a worker merely to “implement the feature.” Give it enough context to succeed without inheriting the coordinator's entire chat.

## Background execution loop

1. Load the official, live Orca orchestration guide (`orca skills get orchestration --full`, using the executable appropriate to the current Orca environment).
2. Create a Run for the user-visible objective.
3. Create tasks with explicit dependencies. Start every ready, non-conflicting task.
4. End the coordinator turn after dispatch. Orca should wake it on worker completion, question, or escalation; do not hide messages by polling from a separate watcher.
5. Process worker questions and completion receipts in order.
6. Review evidence. Send focused corrections to the same dispatch when continuity helps; create a new retry only when the existing worker is unusable or isolation is needed.
7. Release finished workers after evidence is retained. Keep a worker open only when the user intends to continue its chat.

## State mapping

| OpenSpec | Orca | Agent memory |
|---|---|---|
| unchecked task | pending/ready/dispatched | active record |
| checked task | completed dispatch accepted | completed record |
| blocked requirement | blocked task or decision gate | blocker and next decision |
| archived change | no live dispatches | stable outcome and decisions |

Runtime status alone must not check an OpenSpec box. Acceptance requires evidence matching the task contract.

## Retry boundary

On failure, first classify the cause: unclear contract, missing dependency, environment failure, implementation error, or architecture mismatch. Correct the smallest upstream source. Avoid repeated blind retries. After two failed implementation attempts on the same contract, the coordinator should re-examine the plan or ask the user rather than launching another identical worker.
