# OpenSpec integration

Use OpenSpec as the local agreement layer between the user, coordinator, and workers. In projects prepared by this skill, the entire `openspec/` tree and generated `.agents/` workflows are ignored and must not be committed.

## Initialization

Prefer the official CLI at the repository root:

```bash
openspec init <repo-root> --tools agents --profile core --no-animation --no-copilot-cloud
```

The `agents` target installs the standard OpenSpec skills under ignored `.agents/` without generating provider-specific directories. The core workflow provides explore, propose, apply, update, sync, and archive skills. Worker selection still happens dynamically through Orca routing.

Managed CLI calls set `XDG_CONFIG_HOME` to `.agent-workspace/openspec-config/` and disable telemetry. This keeps OpenSpec configuration local to the ignored workspace and makes bootstrap repeatable in restricted agent environments.

Do not use `--force` during generic bootstrap. Refreshing an existing installation with `openspec update <repo-root>` is a separate, explicitly reviewed action because it can regenerate tool integrations.

## Artifact lifecycle

The default flow is:

```text
proposal -> delta specs -> design -> tasks -> implementation -> verification -> archive
```

- `proposal.md`: why and high-level scope.
- `specs/`: ADDED, MODIFIED, and REMOVED behavioral requirements with scenarios.
- `design.md`: technical approach and decisions; omit only when the change truly needs no design.
- `tasks.md`: small implementation checkboxes, each with verification.

OpenSpec owns artifact coherence and is the sole source of truth for the plan. Workers may suggest corrections discovered during implementation but should not silently change product intent. `MEMORY.md` and runtime records link to a change instead of copying proposal, specs, design, or tasks.

## Mapping to Orca

- One OpenSpec change normally maps to one Orca Run.
- Read task IDs and completion state from `openspec instructions apply --change <change> --json`.
- A cohesive `tasks.md` group maps to one Orca Task when a single worker can own it safely; every accepted runtime record stores the exact OpenSpec task ID.
- Dependencies in code or generated artifacts become Orca task dependencies.
- Separate tasks that can be verified independently and do not write the same files may run concurrently.
- A checked box means the coordinator accepted evidence, not merely that an executor reported success. `workspace.py complete --outcome accepted` verifies both the checkbox and strict change validation.

Keep task IDs in the active memory record rather than adding runtime-specific IDs throughout OpenSpec documents.

## Archive boundary

Before archive:

1. all relevant task boxes are checked;
2. requirements have verification evidence;
3. the final implementation matches any revised design;
4. active records are closed or explicitly carried forward;
5. durable decisions are recorded;
6. the user has authorized any integration action that is not already implied by the task.

OpenSpec archive preserves proposal, design, tasks, and deltas as the canonical change history. Agent memory keeps only runtime evidence, routing, blockers, and decision references. Complete runtime records before archive so the CLI can still resolve their active task IDs.

Because OpenSpec is local-only in this workflow, collaboration and recovery depend on the local workspace. The skill must not present local OpenSpec files as repository documentation or attempt to add them to Git.
