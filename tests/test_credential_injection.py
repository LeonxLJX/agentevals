"""Per-evaluation judge credential injection tests.

Exercises the agentevals construction path (build_eval_metric -> get_evaluator ->
_inject_judge_credential) without making any network calls, the fail-closed
behavior on an unresolved credential, the concurrency isolation that motivates the
ContextVar design, and a guard test that fails loudly if the ADK judge seam moves.
"""

from __future__ import annotations

import asyncio
import logging
import os

from agentevals.builtin_metrics import (
    _inject_judge_credential,
    build_eval_metric,
    evaluate_builtin_metric,
    get_evaluator,
)
from agentevals.resolvers import (
    get_resolved_credential,
    reset_resolved_credentials,
    set_resolved_credentials,
)


def _judge_evaluator(model_id: str = "openai/gpt-4o"):
    return get_evaluator(build_eval_metric("final_response_match_v2", model_id, 0.5))


class TestInjection:
    def test_litellm_judge_uses_injected_key_not_env(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        evaluator = _judge_evaluator()

        _inject_judge_credential(evaluator, "sk-injected", base_url="https://proxy.local")

        args = evaluator._judge_model._additional_args
        assert args["api_key"] == "sk-injected"
        assert args["base_url"] == "https://proxy.local"

    def test_gemini_judge_client_replaced(self):
        evaluator = get_evaluator(
            build_eval_metric("rubric_based_final_response_quality_v1", "gemini-2.5-flash", 0.5, rubrics=["good?"])
        )
        # Seeded only by injection: an un-injected judge builds its client lazily on
        # first access, so the cache slot is absent until we replace it.
        assert "api_client" not in evaluator._judge_model.__dict__

        _inject_judge_credential(evaluator, "gem-injected")

        assert "api_client" in evaluator._judge_model.__dict__

    def test_inject_is_noop_on_non_judge_evaluator(self, caplog):
        evaluator = get_evaluator(build_eval_metric("tool_trajectory_avg_score", None, 0.5))
        with caplog.at_level(logging.WARNING):
            _inject_judge_credential(evaluator, "sk-x")
        assert not hasattr(evaluator, "_judge_model")
        assert any("not judge-backed" in r.getMessage() for r in caplog.records)


class TestFailClosed:
    async def test_unresolved_credential_errors_instead_of_ambient_auth(self):
        result = await evaluate_builtin_metric(
            metric_name="final_response_match_v2",
            actual_invocations=[],
            expected_invocations=[object()],
            judge_model="openai/gpt-4o",
            threshold=0.5,
            credential_ref="judge-openai",
        )
        assert result.score is None
        assert "judge-openai" in result.error
        assert "credentialRefs" in result.error


class TestConcurrencyIsolation:
    async def test_concurrent_runs_do_not_cross_talk(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        env_before = dict(os.environ)

        async def run_one(key: str) -> str:
            set_resolved_credentials({"judge": key})
            # Yield after setting so the sibling task sets its own value before we
            # read back. With a shared global instead of a ContextVar, both tasks
            # would observe the last writer's key and this assertion would fail.
            await asyncio.sleep(0)
            evaluator = _judge_evaluator()
            _inject_judge_credential(evaluator, get_resolved_credential("judge"))
            return evaluator._judge_model._additional_args["api_key"]

        first, second = await asyncio.gather(run_one("sk-AAA"), run_one("sk-BBB"))

        assert first == "sk-AAA"
        assert second == "sk-BBB"
        assert dict(os.environ) == env_before


class TestAdkSeamGuard:
    """Fails loudly if the version-pinned ADK judge seam moves."""

    def test_llm_as_judge_exposes_setup_auto_rater(self):
        from google.adk.evaluation.llm_as_judge import LlmAsJudge

        assert hasattr(LlmAsJudge, "_setup_auto_rater")

    def test_judge_evaluator_exposes_seam_attributes(self):
        evaluator = _judge_evaluator()
        assert hasattr(evaluator, "_judge_model")
        assert hasattr(evaluator, "_judge_model_options")
        assert evaluator._judge_model_options.judge_model == "openai/gpt-4o"

    def test_litellm_forwards_api_key_kwarg(self):
        from google.adk.models.lite_llm import LiteLlm

        assert LiteLlm(model="openai/gpt-4o", api_key="sentinel")._additional_args["api_key"] == "sentinel"
