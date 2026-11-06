# Agent memory

This directory stores execution context outside chat history.

- `active/`: one live record per owned task.
- `completed/`: compact accepted outcomes and evidence.
- `decisions/`: durable project decisions and their rationale.
- `.templates/`: copyable record formats.

Create an active record at dispatch time. Give it one owner, an OpenSpec change, Orca IDs, a next action, and measurable acceptance criteria. Update only at meaningful transitions.

After coordinator acceptance, remove transient narration, retain evidence and residual risks, then move the record to `completed/`. Extract cross-task decisions into `decisions/`. Update root `MEMORY.md` only when stable project-wide knowledge changed.

Do not store secrets, production payloads, raw terminal logs, full chat transcripts, or duplicated OpenSpec documents here.
