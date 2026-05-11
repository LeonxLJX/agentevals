# Custom result sink plugin

This folder is a tiny installable Python package that registers a result **sink** with agentevals via setuptools **entry points**. The worker fans out partial/final/error events to every configured sink in addition to the database.

## What gets implemented

- **`DemoNdjsonSink`** — subclasses `ResultSink` from `agentevals.run.sinks` and appends one JSON object per line to `path` from the run spec (same pattern as the built-in `file` sink, with a `"demo": true` marker on each line).
- **`create_demo_sink(spec)`** — factory callable; must accept the full sink dict from the run spec and return a `ResultSink` (see return type in code).

The entry point **name** (`demo_ndjson` in `pyproject.toml`) is the **`kind`** string clients put under `spec.sinks`.

## Install (local dev)

From the agentevals repo root, install the framework first, then this example:

```bash
uv pip install -e .
uv pip install -e examples/custom_sink
```

Restart the agentevals process so `importlib.metadata` picks up the new distribution.

PyPI-style usage is the same: depend on `agentevals-example-custom-sink` next to `agentevals-cli`, install both into the server environment, restart.

## Configure runs

Async runs are submitted with **`POST /api/runs`**. Put your sink in **`spec.sinks`** (requires Postgres storage — see main docs).

Example body (use **absolute** `path` on the host where the agentevals process runs when possible). **`path` must be a file path** (e.g. `/tmp/demo.ndjson`). If `path` is an **existing directory** (including `"."` for the process working directory), output goes to `<path>/agentevals-demo-sink.ndjson`, or `<path>/<filename>` if you add an optional `"filename"` field next to `path` in the sink dict.

The `inline` object must contain real trace data (Jaeger JSON or OTLP), not an empty object.

```json
{
  "spec": {
    "approach": "trace_replay",
    "target": {
      "kind": "inline",
      "traceFormat": "jaeger-json",
      "inline": {
        "data": [
          {
            "traceID": "61646461646164646164616461646164",
            "spans": [
              {
                "traceID": "61646461646164646164616461646164",
                "spanID": "6164616461646164",
                "operationName": "demo-op",
                "startTime": 1000000,
                "duration": 100000,
                "tags": [],
                "logs": [],
                "references": [],
                "processID": "p1"
              }
            ],
            "processes": { "p1": { "serviceName": "demo" } }
          }
        ]
      }
    },
    "sinks": [{ "kind": "demo_ndjson", "path": "/tmp/agentevals-demo.ndjson" }]
  }
}
```

You can list several sinks; they run in parallel. Built-in kinds are `stdout`, `file`, and `http_webhook`.

## Publishing your own sink

1. Implement `ResultSink` from `agentevals.run.sinks` (subclass the protocol, or provide the three async methods).
2. Expose a factory `def create_*(spec: dict) -> ResultSink`.
3. Add the following to your `pyproject.toml`:

```toml
[project.entry-points."agentevals.sinks"]
your_kind = "your_package.module:your_factory"
```

4. Install the package into the **same environment** as `agentevals serve`, restart, and reference `"kind": "your_kind"` in `spec.sinks`.
