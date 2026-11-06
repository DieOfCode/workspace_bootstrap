# Agent workflow

## Roles

- **Coordinator:** plans with local OpenSpec, decomposes work, routes tasks to enabled Orca agents, resolves questions, and accepts evidence.
- **Executor:** implements one bounded task in its worktree and updates the matching active JSON record.
- **Verifier:** runs only when explicitly requested, starts with fresh context, and is read-only by default.

## Lifecycle

1. Inspect current behavior and create or update a local OpenSpec change.
2. Create active task JSON records with precise read/write/forbidden scopes.
3. Run `workspace.py risk` and `workspace.py conflicts` before dispatch.
4. Sequence definite write overlaps; parallelize only non-conflicting tasks in separate worktrees.
5. Let Orca wake the coordinator on questions, failures, and completion.
6. Verify implementation evidence against OpenSpec.
7. Run `workspace.py complete` after acceptance or closure.
8. Run `workspace.py compact` during maintenance to create 30-day monthly rollups.

All files described here are local-only and covered by the project's `.gitignore`.
