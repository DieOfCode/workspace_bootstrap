# Local agent workspace

Everything in this directory is local execution state and must remain ignored by Git. OpenSpec—not this directory—owns proposals, requirements, design, implementation tasks, progress, and archived change history.

- `policy.json`: detected project facts and orchestration policy.
- `openspec-config/`: project-local OpenSpec CLI configuration; telemetry is disabled for managed commands.
- `reports/`: optional project-doctor reports.
- `memory/active/`: one machine-readable JSON record per active task.
- `memory/completed/raw/`: immutable completed task JSON.
- `memory/completed/records/`: compact execution outcomes linked to OpenSpec tasks.
- `memory/completed/rollups/`: monthly summaries for older work.
- `memory/decisions/`: durable decision rationale.
- `memory/verifications/`: explicitly requested verifier reports.
- `templates/`: copyable local record formats.

Use the skill's `workspace.py` commands instead of manually moving lifecycle files. Never store credentials, production data, raw chat transcripts, or unredacted secrets here.
