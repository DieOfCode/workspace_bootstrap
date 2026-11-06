# Project memory model

The memory system prevents chat context from becoming the only record of progress and rationale.

## Layers

### Stable memory: `MEMORY.md`

Keep verified facts that remain useful across many tasks:

- architecture and service boundaries;
- canonical commands;
- durable constraints and conventions;
- important risks and non-obvious behavior;
- links to current OpenSpec changes and decisions.

Keep it under roughly 200 lines. Replace stale facts; do not append an endless diary.

### Active memory: `.agent-workspace/memory/active/`

Use one structured JSON record per dispatched unit of work. It answers:

- what is being attempted and by whom;
- which specification and dispatch own it;
- what has been verified;
- what decision or blocker is next.

Update at meaningful transitions, not after every command. Raw logs belong in tooling output or artifacts, not the record.

### Completed memory: `.agent-workspace/memory/completed/`

Use `workspace.py complete` after coordinator acceptance or closure. For accepted work, the corresponding OpenSpec task must already be checked and the change must pass strict validation. The command preserves runtime JSON and creates a compact record containing routing, execution scope, evidence, decisions, residual risk, and an OpenSpec reference. It does not copy the plan.

Records are organized by year/month. `workspace.py compact` creates idempotent monthly rollups for records at least 30 days old. Raw and individual records are retained indefinitely.

### Decisions: `.agent-workspace/memory/decisions/`

Create a decision record when the choice is expensive to reverse, affects several tasks, changes a public contract, or would otherwise be repeatedly debated. Include context, considered options, rationale, consequences, and supersession links.

Small local choices stay in the task record.

## Lifecycle

```text
OpenSpec task selected
  -> active JSON record created
  -> discoveries/evidence updated
  -> coordinator verifies
  -> corresponding OpenSpec checkbox checked
  -> decision records extracted
  -> complete command verifies OpenSpec and archives runtime evidence
  -> OpenSpec change validated and explicitly archived after all tasks
  -> compact command creates a monthly rollup after 30 days
  -> stable MEMORY.md updated only if project-wide truth changed
```

Use a stable task key derived from the OpenSpec change and task number, for example `add-rate-limit-2-1`. Rename the file only before dispatch IDs or external links depend on it.

## Conflict and freshness

Each record includes a `Last updated` value and a single owner. When two records conflict, stop parallel work in the overlapping area and let the coordinator reconcile them. Mark obsolete decisions as superseded instead of deleting the reasoning.

Never store credentials, personal data, private keys, tokens, production payloads, or unredacted secrets in project memory.

All memory paths, root `MEMORY.md`, and decision/verifier records are local-only. They must be ignored and absent from the Git index.
