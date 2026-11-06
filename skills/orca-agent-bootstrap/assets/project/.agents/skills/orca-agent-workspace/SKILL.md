---
name: orca-agent-workspace
description: Use the local ignored agent workspace, OpenSpec plan, task records, and validation commands when coordinating or executing work in this project.
---

# Local Orca Agent Workspace

Read the project root `AGENTS.md`, `MEMORY.md`, relevant `openspec/` artifacts, `.agent-workspace/policy.json`, and the assigned active-task JSON before acting.

OpenSpec owns proposal, specs, design, task progress, and archive history. The coordinator owns routing, dependencies, conflict checks, questions, and acceptance. Executors stay inside their declared runtime scopes and return evidence. Verifiers run only after an explicit decision, start from fresh context, and are read-only by default.

Before dispatch, read task IDs with `openspec instructions apply --change <change> --json`, then run `workspace.py risk` and `workspace.py conflicts`. After evidence is accepted, check the corresponding OpenSpec task and run `workspace.py complete`. Before final reporting, run `workspace.py scan-secrets` and `workspace.py validate`.

All files in `AGENTS.md`, `MEMORY.md`, `openspec/`, `.agents/`, and `.agent-workspace/` are local-only and must remain absent from the Git index.
