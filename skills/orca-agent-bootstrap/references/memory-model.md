# Project memory model

The memory system prevents chat context from becoming the only record of progress and rationale.

## Layers

### Stable memory: `MEMORY.md`

Keep verified facts that remain useful across many tasks:

- architecture and service boundaries;
- canonical commands;
- durable constraints and conventions;
- important risks and non-obvious behavior;
- links to current specs and decisions.

Keep it under roughly 200 lines. Replace stale facts; do not append an endless diary.

### Active memory: `docs/agent-memory/active/`

Use one record per dispatched unit of work. It answers:

- what is being attempted and by whom;
- which specification and dispatch own it;
- what has been verified;
- what decision or blocker is next.

Update at meaningful transitions, not after every command. Raw logs belong in tooling output or artifacts, not the record.

### Completed memory: `docs/agent-memory/completed/`

Move and compact the active record after coordinator acceptance. Preserve outcome, affected areas, evidence, decisions, residual risk, and follow-ups. Remove transient narration.

Organize by year/month when the directory becomes large. A completed record is an index to evidence, not a second implementation report.

### Decisions: `docs/agent-memory/decisions/`

Create a decision record when the choice is expensive to reverse, affects several tasks, changes a public contract, or would otherwise be repeatedly debated. Include context, considered options, rationale, consequences, and supersession links.

Small local choices stay in the task record.

## Lifecycle

```text
OpenSpec task selected
  -> active record created
  -> discoveries/evidence updated
  -> coordinator verifies
  -> decision records extracted
  -> compacted record moved to completed
  -> stable MEMORY.md updated only if project-wide truth changed
```

Use a stable task key derived from the OpenSpec change and task number, for example `add-rate-limit-2-1`. Rename the file only before dispatch IDs or external links depend on it.

## Conflict and freshness

Each record includes a `Last updated` value and a single owner. When two records conflict, stop parallel work in the overlapping area and let the coordinator reconcile them. Mark obsolete decisions as superseded instead of deleting the reasoning.

Never store credentials, personal data, private keys, tokens, production payloads, or unredacted secrets in project memory.
