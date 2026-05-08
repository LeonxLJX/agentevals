"""Minimal NDJSON sink registered via setuptools entry points."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any
from uuid import UUID

from agentevals.run.sinks import ResultSink
from agentevals.storage.models import Result


def _result_payload(r: Result) -> dict:
    return r.model_dump(mode="json", by_alias=True)


_DEFAULT_FILENAME = "agentevals-demo-sink.ndjson"


def _resolve_output_file(spec: dict[str, Any]) -> Path:
    """If ``path`` is an existing directory (including ``.``), write NDJSON inside it."""
    p = Path(spec["path"]).expanduser()
    if p.exists() and p.is_dir():
        name = spec.get("filename") or _DEFAULT_FILENAME
        return p / name
    return p


class DemoNdjsonSink(ResultSink):
    """Concrete :class:`~agentevals.run.sinks.ResultSink`; append-only JSON lines with a ``demo`` marker."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = asyncio.Lock()

    async def _write(self, payload: dict) -> None:
        async with self._lock:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with self._path.open("a") as f:  # noqa: ASYNC230
                f.write(json.dumps(payload) + "\n")

    async def emit_partial(self, run_id: UUID, results: list[Result], attempt: int) -> None:
        for r in results:
            await self._write(
                {
                    "phase": "partial",
                    "run_id": str(run_id),
                    "attempt": attempt,
                    "demo": True,
                    "result": _result_payload(r),
                }
            )

    async def emit_final(self, run_id: UUID, summary: dict, attempt: int) -> None:
        await self._write(
            {"phase": "final", "run_id": str(run_id), "attempt": attempt, "demo": True, "summary": summary}
        )

    async def emit_error(self, run_id: UUID, error: str, attempt: int) -> None:
        await self._write({"phase": "error", "run_id": str(run_id), "attempt": attempt, "demo": True, "error": error})


def create_demo_sink(spec: dict[str, Any]) -> ResultSink:
    """Entry-point factory: returns a :class:`ResultSink`; ``kind`` must be ``demo_ndjson`` (see pyproject).

    ``path`` should normally be a **file** path. If it points at an existing directory (e.g. ``.`` or ``/tmp``),
    lines are appended to ``<path>/agentevals-demo-sink.ndjson``, or ``<path>/<filename>`` if ``filename`` is set.
    """
    return DemoNdjsonSink(_resolve_output_file(spec))
