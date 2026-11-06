# Local agent workspace

Everything in this directory is local execution state and must remain ignored by Git.

- `policy.json`: detected project facts and orchestration policy.
- `reports/`: optional project-doctor reports.
- `memory/active/`: one machine-readable JSON record per active task.
- `memory/completed/raw/`: immutable completed task JSON.
- `memory/completed/records/`: compact human-readable outcomes.
- `memory/completed/rollups/`: monthly summaries for older work.
- `memory/decisions/`: durable decision rationale.
- `memory/verifications/`: explicitly requested verifier reports.
- `templates/`: copyable local record formats.

Use the skill's `workspace.py` commands instead of manually moving lifecycle files. Never store credentials, production data, raw chat transcripts, or unredacted secrets here.
