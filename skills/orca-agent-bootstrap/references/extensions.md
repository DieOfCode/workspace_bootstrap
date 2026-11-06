# Optional extensions

Apply these only when their cost matches the project.

## Independent verification

Dispatch a fresh-context verifier for authentication, payments, migrations, concurrency, security boundaries, and broad refactors. Require a requirement-to-evidence table and a verdict. Keep implementation and acceptance authority separate.

## Model routing

Record a simple policy in `AGENTS.md`:

- coordinator route: capable agent/model for discovery, architecture, decomposition, conflict resolution, and final review;
- executor route: any enabled Orca agent/model whose capabilities, host, latency, and cost match the bounded task;
- verifier route: preferably a different agent/model family when independent reasoning materially reduces correlated errors;
- specialist route: an agent with the required UI, browser, security, database, or platform tools.

The coordinator's own harness is not the worker allow-list. A Codex coordinator can route to Cursor or Antigravity, and the reverse, when those agent IDs are enabled on the worker server. Use capability and risk rather than task size or provider loyalty. Never put an under-specified task on a cheaper model.

## Context budgets

Set limits for worker contracts and memory records. Provide paths and targeted excerpts instead of whole repositories. When a task grows beyond one cohesive outcome, split it before dispatch.

## Conflict-aware scheduling

Add an `Expected files` field to active records. The coordinator can run tasks concurrently only when their write sets do not overlap or an explicit integration order exists.

## Verification matrix

For each OpenSpec scenario, track the test, command, manual observation, or artifact that proves it. Use this as the acceptance gate and as input to CI.

## Recovery policy

Define what happens when a worker stops, asks for credentials, fails verification, or produces an unreviewable diff. Prefer correcting the plan or environment over blind retries. Preserve failed-task evidence when it explains later decisions.

## Automated hygiene

Useful later additions include:

- a project doctor that checks required commands, stale links, active records without owners, and finished tasks left active;
- CI validation for OpenSpec and memory schemas;
- periodic compaction of completed records into release or milestone summaries;
- secret scanning for committed agent artifacts;
- metrics for lead time, retry rate, verification failures, and model cost without storing prompts or sensitive content.
