# Agent workflow

## Roles

- **Coordinator:** plans with local OpenSpec, decomposes work, routes tasks to enabled Orca agents, resolves questions, and accepts evidence.
- **Executor:** implements one bounded task in its worktree and updates the matching active JSON record.
- **Verifier:** runs only when explicitly requested, starts with fresh context, and is read-only by default.

## Lifecycle

1. Use OpenSpec explore/propose/update workflows for the canonical local plan.
2. Read task IDs with `openspec instructions apply --change <change> --json`; create active task JSON records with exact OpenSpec references and precise runtime scopes.
3. Run `workspace.py risk` and `workspace.py conflicts` before dispatch.
4. Sequence definite write overlaps; parallelize only non-conflicting tasks in separate worktrees.
5. Let Orca wake the coordinator on questions, failures, and completion.
6. Verify implementation evidence against OpenSpec, then check the accepted task in OpenSpec `tasks.md`.
7. Run `workspace.py complete`; accepted completion requires that checked task and strict change validation.
8. After all tasks, explicitly use OpenSpec sync/archive workflows. OpenSpec owns plan history; runtime memory keeps only execution evidence.
9. Run `workspace.py compact` during maintenance to create 30-day operational rollups.

All files described here are local-only and covered by the project's `.gitignore`.
