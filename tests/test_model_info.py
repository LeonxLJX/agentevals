"""Regression tests for per-invocation model info extraction.

Covers https://github.com/agentevals-dev/agentevals/issues/204:
`_extract_model_info_from_trace` aggregated LLM spans across the whole trace
for every invocation, so each invocation reported the session-wide totals.
Now the converter records which LLM spans each invocation was built from and
ws_server aggregates only those spans.
"""

import json

from agentevals.converter import convert_trace
from agentevals.loader.base import Span, Trace
from agentevals.streaming.ws_server import StreamingTraceManager


def _adk_llm_span(span_id: str, model: str, input_tokens: int, output_tokens: int, start_time: int) -> Span:
    """Build an ADK call_llm span with distinct usage metadata and user text."""
    return Span(
        trace_id="t1",
        span_id=span_id,
        parent_span_id="invoke",
        operation_name="call_llm",
        start_time=start_time,
        duration=1000,
        tags={
            "otel.scope.name": "gcp.vertex.agent",
            "gcp.vertex.agent.llm_request": json.dumps(
                {
                    "model": model,
                    "contents": [
                        {"role": "user", "parts": [{"text": f"hello from {span_id}"}]},
                    ],
                }
            ),
            "gcp.vertex.agent.llm_response": json.dumps(
                {
                    "content": {"parts": [{"text": f"answer from {span_id}"}], "role": "model"},
                    "usage_metadata": {
                        "prompt_token_count": input_tokens,
                        "candidates_token_count": output_tokens,
                    },
                }
            ),
            "gen_ai.provider.name": "vertex_ai",
            "gen_ai.response.finish_reasons": "stop",
        },
    )


def _two_invocation_adk_trace() -> Trace:
    """ADK trace with two invoke_agent spans, each owning its own LLM spans."""
    invoke1 = Span(
        trace_id="t1",
        span_id="invoke1",
        parent_span_id=None,
        operation_name="invoke_agent agent_a",
        start_time=1000,
        duration=20000,
        tags={"otel.scope.name": "gcp.vertex.agent", "gen_ai.operation.name": "invoke_agent"},
    )
    invoke2 = Span(
        trace_id="t1",
        span_id="invoke2",
        parent_span_id=None,
        operation_name="invoke_agent agent_b",
        start_time=30000,
        duration=20000,
        tags={"otel.scope.name": "gcp.vertex.agent", "gen_ai.operation.name": "invoke_agent"},
    )

    llm1 = _adk_llm_span("llm1", "model-a", 100, 20, 2000)
    llm2a = _adk_llm_span("llm2a", "model-b", 300, 50, 31000)
    llm2b = _adk_llm_span("llm2b", "model-b", 400, 60, 32000)

    llm1.parent_span_id = "invoke1"
    llm2a.parent_span_id = "invoke2"
    llm2b.parent_span_id = "invoke2"
    invoke1.children.append(llm1)
    invoke2.children.extend([llm2a, llm2b])

    return Trace(
        trace_id="t1",
        root_spans=[invoke1, invoke2],
        all_spans=[invoke1, llm1, invoke2, llm2a, llm2b],
    )


class TestPerInvocationSpans:
    def test_conversion_tracks_each_invocations_own_llm_spans(self):
        result = convert_trace(_two_invocation_adk_trace())
        assert len(result.invocations) == 2
        assert len(result.invocation_llm_spans) == 2
        assert [s.span_id for s in result.invocation_llm_spans[0]] == ["llm1"]
        assert [s.span_id for s in result.invocation_llm_spans[1]] == ["llm2a", "llm2b"]

    def test_model_info_is_per_invocation_not_session_wide(self):
        manager = StreamingTraceManager()
        trace = _two_invocation_adk_trace()

        info_a = manager._extract_model_info_from_llm_spans([trace.all_spans[1]])
        info_b = manager._extract_model_info_from_llm_spans([trace.all_spans[3], trace.all_spans[4]])

        assert info_a["inputTokens"] == 100
        assert info_a["outputTokens"] == 20
        assert info_b["inputTokens"] == 700  # 300 + 400, only invocation B's spans
        assert info_b["outputTokens"] == 110  # 50 + 60

        # The bug made every invocation report identical session-wide totals.
        assert info_a["inputTokens"] != info_b["inputTokens"]
        assert info_a["outputTokens"] != info_b["outputTokens"]

    def test_empty_spans_yield_empty_model_info(self):
        manager = StreamingTraceManager()
        assert manager._extract_model_info_from_llm_spans([]) == {}
