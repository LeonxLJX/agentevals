# Run History

Run history turns each evaluation into a durable record you can revisit, group, and trend over time. When agentevals runs with the Postgres storage backend, every evaluation (whether an uploaded trace file or a live streaming session) is persisted as a **run** with its per case scores, and the UI's **Run History** view lets you explore how an agent or eval set performs across many runs.

Without the Postgres backend, agentevals is stateless: evaluations still work and results show on the dashboard, but nothing is persisted and the run-history endpoints return `503`.

## Enabling durable storage

Run history requires the Postgres storage backend. It is opt in.

### Local development

The quickest path uses the Makefile target, which starts a throwaway Postgres container, applies migrations, and serves the app wired to it:

```bash
make dev-backend-pg
```

That is equivalent to:

```bash
export AGENTEVALS_STORAGE_BACKEND=postgres
export AGENTEVALS_DATABASE_URL=postgresql://agentevals:agentevals@localhost:5432/agentevals
uv run agentevals migrate up          # apply schema migrations
uv run agentevals serve --dev         # serve with the Postgres backend
```

Run the UI in a second terminal (`cd ui && npm run dev`) and open the **Run History** tab.

> The `make pg-up` container runs with `--rm` and no volume, so its data is ephemeral: `make pg-down` (or a reboot) resets your run history. Point `AGENTEVALS_DATABASE_URL` at a persistent Postgres if you want runs to survive across sessions.

### Configuration reference

| Variable | Purpose |
|----------|---------|
| `AGENTEVALS_STORAGE_BACKEND` | `postgres` to enable durable storage; anything else (default) keeps the in-memory backend |
| `AGENTEVALS_DATABASE_URL` | Postgres DSN, e.g. `postgresql://user:pass@host:5432/dbname` |
| `AGENTEVALS_DATABASE_URL_FILE` | Path to a file containing the DSN (preferred over the inline variable; useful for mounted secrets) |
| `AGENTEVALS_DATABASE_SCHEMA` | Schema name to use (default `agentevals`) |

On startup with `storage.backend=postgres` the app applies any pending migrations (advisory-lock protected, safe across replicas). For deployment via Helm, see the [Postgres backend section of the README](../README.md#postgres-backend-apiruns).

## How runs get persisted

A run is created once per evaluation, best effort: if persistence fails the evaluation result is still returned to the caller. Both evaluation paths persist:

- **Uploaded traces** (`POST /api/evaluate`): the run aggregates every uploaded trace as one evaluation.
- **Live sessions** (streaming dev server): scoring sessions from the UI persists one run per "Evaluate" click, aggregating the sessions it scored.

Each run stores a pre-aggregated `summary` plus one `result` row per (eval case, evaluator):

```jsonc
// run.summary
{
  "trace_count": 8,
  "result_counts": { "passed": 6, "failed": 2, "errored": 0, "skipped": 0 },
  "per_metric": {
    "tool_trajectory_avg_score": { "passed": 7, "failed": 1, "errored": 0, "skipped": 0, "avg_score": 0.94 }
  },
  "agents": ["langchain-agent", "openai-agents-agent"],
  "performance_metrics": { "models": ["gpt-4o"], /* tokens, latency, counts */ },
  "errors": []
}
```

## Exploring runs in the UI

Open **Run History** from the sidebar. It reads from `GET /api/runs`, so it shows the same friendly notice if durable storage is not configured.

- **Trends.** A pass-rate line and a per-metric average-score line plot across runs over time, so regressions and improvements are visible at a glance.
- **Group by.** Toggle between grouping by **eval set** or by **agent**, then pick a specific group to isolate its runs and trends. The pass-rate chart draws one line per agent.
- **History table.** Every run with its status, eval set, agent, trace count, pass/fail counts, pass-rate bar, duration, and models. Click a row to open the run detail.
- **Run detail.** For a single run: the evaluator configuration (metrics, thresholds, judge model), the golden eval set it was scored against, and per eval case results. Tool-trajectory results expand to an expected vs actual diff per invocation, showing exactly where the run diverged from the reference.

### What is and is not persisted

Run detail is an *evaluation record*, not a full trace record. It faithfully shows the expected behavior, each metric's pass or fail, and (for trajectory metrics) where the actual tool calls diverged. It does not retain the raw trace spans or timeline, and text-similarity metrics keep only their score, not the actual response text. To replay a full trace, use the live inspector at evaluation time.

## Agent identity and grouping

Runs group by **agent** using the OpenTelemetry `service.name` resource attribute, the cross-framework identifier for a service. Set it on your agent with the standard `OTEL_SERVICE_NAME` environment variable:

```bash
OTEL_SERVICE_NAME=my-agent python my_agent.py
```

The zero-code examples set this for you (for example `service.name=langchain-agent`). When `service.name` is absent, agentevals falls back to the framework agent name (`gen_ai.agent.name`); it never falls back to a model or span operation name, so a group is always a real agent identity.

## Golden reference handling

When you score other agents against a golden session, the golden defines the eval set and therefore matches itself trivially. To keep scoring meaningful, the golden is excluded from pass or fail counts, the agent list, and the results table, but its latency and token usage are still plotted in the performance charts (labeled as the reference) so you can compare the scored agents against the baseline.

## HTTP API

All endpoints return `503` (with a hint pointing at `AGENTEVALS_STORAGE_BACKEND=postgres`) when durable storage is not configured.

| Method + path | Description |
|---------------|-------------|
| `GET /api/runs` | List runs, newest first. Filter with `status`, `limit` (1-1000), and `before` (a `created_at` cursor for pagination) |
| `GET /api/runs/{run_id}` | Fetch a single run (spec + summary) |
| `GET /api/runs/{run_id}/results` | List the per (eval case, evaluator) result rows for a run |
| `POST /api/runs` | Submit a run for asynchronous execution by the in-process worker; idempotent on `run_id` |
| `POST /api/runs/{run_id}/cancel` | Request cancellation of a queued or running run (idempotent) |

Interactive API docs are available at `/docs` (Swagger) and `/redoc` while the server is running.
