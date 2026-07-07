"""Jaeger JSON trace loader."""

from __future__ import annotations

import json
import logging
from typing import Any

from .base import Span, Trace, TraceLoader

logger = logging.getLogger(__name__)


class JaegerJsonLoader(TraceLoader):
    """Loads traces from Jaeger JSON export files.

    Expected format::

        {
            "data": [
                {
                    "traceID": "...",
                    "spans": [
                        {
                            "traceID": "...",
                            "spanID": "...",
                            "operationName": "...",
                            "references": [{"refType": "CHILD_OF", "spanID": "..."}],
                            "startTime": <microseconds>,
                            "duration": <microseconds>,
                            "tags": [{"key": "...", "type": "...", "value": ...}],
                            ...
                        },
                        ...
                    ]
                },
                ...
            ]
        }
    """

    def format_name(self) -> str:
        return "jaeger-json"

    def load(self, source: str) -> list[Trace]:
        with open(source) as f:
            raw = json.load(f)

        if not isinstance(raw, dict) or "data" not in raw:
            raise ValueError(f"Invalid Jaeger JSON format: expected top-level 'data' key in {source}")

        traces: list[Trace] = []
        for trace_data in raw["data"]:
            trace = self._parse_trace(trace_data)
            if trace:
                traces.append(trace)

        logger.info("Loaded %d trace(s) from %s", len(traces), source)
        return traces

    def _parse_trace(self, trace_data: dict[str, Any]) -> Trace | None:
        trace_id = trace_data.get("traceID", "")
        raw_spans = trace_data.get("spans", [])

        if not raw_spans:
            logger.warning("Trace %s has no spans, skipping", trace_id)
            return None

        spans_by_id: dict[str, Span] = {}
        for raw_span in raw_spans:
            span = self._parse_span(raw_span)
            spans_by_id[span.span_id] = span

        root_spans: list[Span] = []
        for span in spans_by_id.values():
            if span.parent_span_id and span.parent_span_id in spans_by_id:
                spans_by_id[span.parent_span_id].children.append(span)
            else:
                root_spans.append(span)

        for span in spans_by_id.values():
            span.children.sort(key=lambda s: s.start_time)

        root_spans.sort(key=lambda s: s.start_time)

        return Trace(
            trace_id=trace_id,
            root_spans=root_spans,
            all_spans=list(spans_by_id.values()),
        )

    def _parse_span(self, raw_span: dict[str, Any]) -> Span:
        parent_span_id: str | None = None
        for ref in raw_span.get("references", []):
            if ref.get("refType") == "CHILD_OF":
                parent_span_id = ref.get("spanID")
                break

        # Jaeger tags are an array of {key, type, value} — flatten to dict
        tags: dict[str, Any] = {}
        for tag in raw_span.get("tags", []):
            tags[tag["key"]] = tag["value"]

        return Span(
            trace_id=raw_span.get("traceID", ""),
            span_id=raw_span.get("spanID", ""),
            parent_span_id=parent_span_id,
            operation_name=raw_span.get("operationName", ""),
            start_time=raw_span.get("startTime", 0),
            duration=raw_span.get("duration", 0),
            tags=tags,
        )
