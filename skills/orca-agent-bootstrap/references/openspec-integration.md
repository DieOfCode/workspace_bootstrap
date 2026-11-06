# OpenSpec integration

Use OpenSpec as the agreement layer between the user, coordinator, and workers. Do not reimplement OpenSpec's schemas inside this skill.

## Initialization

Prefer the official CLI at the repository root:

```bash
openspec init --tools agents --profile core --no-animation --no-copilot-cloud
```

The `agents` tool target creates shared workflow skills under `.agents/`, which Orca can expose to compatible agents. Add explicit tool IDs such as `codex` or `claude` only when the project needs their tool-specific placements.

Do not use `--force` during generic bootstrap. If an existing installation needs refresh, preview first:

```bash
openspec update --dry-run --json
```

## Artifact lifecycle

The default flow is:

```text
proposal -> delta specs -> design -> tasks -> implementation -> verification -> archive
```

- `proposal.md`: why and high-level scope.
- `specs/`: ADDED, MODIFIED, and REMOVED behavioral requirements with scenarios.
- `design.md`: technical approach and decisions; omit only when the change truly needs no design.
- `tasks.md`: small implementation checkboxes, each with verification.

The coordinator owns artifact coherence. Workers may suggest corrections discovered during implementation but should not silently change product intent.

## Mapping to Orca

- One OpenSpec change normally maps to one Orca Run.
- A cohesive `tasks.md` group maps to one Orca Task when a single worker can own it safely.
- Dependencies in code or generated artifacts become Orca task dependencies.
- Separate tasks that can be verified independently and do not write the same files may run concurrently.
- A checked box means the coordinator accepted evidence, not merely that an executor reported success.

Keep task IDs in the active memory record rather than adding runtime-specific IDs throughout OpenSpec documents.

## Archive boundary

Before archive:

1. all relevant task boxes are checked;
2. requirements have verification evidence;
3. the final implementation matches any revised design;
4. active records are closed or explicitly carried forward;
5. durable decisions are recorded;
6. the user has authorized any integration action that is not already implied by the task.

OpenSpec archive preserves proposal, design, tasks, and deltas as history. Agent memory should point to that archive instead of copying it.
