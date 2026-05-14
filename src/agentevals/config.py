"""Configuration for agentevals runs."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel


def _normalize_trajectory_match_type(v: str | None) -> str | None:
    valid = {"EXACT", "IN_ORDER", "ANY_ORDER"}
    if v is not None and v.upper() not in valid:
        raise ValueError(f"Invalid trajectory_match_type '{v}'. Valid values: {sorted(valid)}")
    return v.upper() if v is not None else v


class BuiltinMetricDef(BaseModel):
    """A built-in ADK metric, optionally with threshold/judge overrides."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    name: str
    type: Literal["builtin"] = "builtin"
    threshold: float | None = Field(default=None, ge=0, le=1)
    judge_model: str | None = None
    trajectory_match_type: str | None = None

    @field_validator("trajectory_match_type")
    @classmethod
    def _validate_trajectory_match_type(cls, v: str | None) -> str | None:
        return _normalize_trajectory_match_type(v)


class BaseEvaluatorDef(BaseModel):
    """Shared fields for all executable evaluator definitions."""

    name: str
    threshold: float = Field(default=0.5, ge=0, le=1)
    timeout: int = Field(default=30, description="Subprocess timeout in seconds.")
    config: dict[str, Any] = Field(default_factory=dict)
    executor: str = Field(default="local", description="Execution environment: 'local' or 'docker' (future).")


class CodeEvaluatorDef(BaseEvaluatorDef):
    """An evaluator implemented as an external code file (Python, JavaScript, etc.)."""

    type: Literal["code"] = "code"
    path: str = Field(description="Path to the evaluator file (.py, .js, .ts, etc.).")

    @field_validator("path")
    @classmethod
    def _validate_extension(cls, v: str) -> str:
        from .custom_evaluators import supported_extensions

        suffix = Path(v).suffix.lower()
        allowed = supported_extensions()
        if suffix not in allowed:
            raise ValueError(f"Unsupported evaluator file extension '{suffix}'. Supported: {sorted(allowed)}")
        return v


class RemoteEvaluatorDef(BaseEvaluatorDef):
    """An evaluator fetched from a remote source (GitHub, registry, etc.)."""

    type: Literal["remote"] = "remote"
    source: str = Field(default="github", description="Evaluator source (e.g. 'github').")
    ref: str = Field(description="Source-specific reference (e.g. path within the repo).")


_VALID_SIMILARITY_METRICS = frozenset(
    {
        "fuzzy_match",
        "bleu",
        "gleu",
        "meteor",
        "cosine",
        "rouge_1",
        "rouge_2",
        "rouge_3",
        "rouge_4",
        "rouge_5",
        "rouge_l",
    }
)


class OpenAIEvalDef(BaseModel):
    """An evaluator that delegates grading to the OpenAI Evals API."""

    type: Literal["openai_eval"] = "openai_eval"
    name: str
    threshold: float = Field(default=0.5, ge=0, le=1)
    timeout: int = Field(default=120, description="Max seconds to wait for the OpenAI eval run to complete.")
    grader: dict[str, Any] = Field(description="OpenAI grader config passed to testing_criteria.")

    @field_validator("grader")
    @classmethod
    def _validate_grader(cls, v: dict[str, Any]) -> dict[str, Any]:
        grader_type = v.get("type")
        if grader_type != "text_similarity":
            raise ValueError(f"Only 'text_similarity' grader type is currently supported, got '{grader_type}'")
        metric = v.get("evaluation_metric")
        if not metric:
            raise ValueError("'evaluation_metric' is required for text_similarity grader")
        if metric not in _VALID_SIMILARITY_METRICS:
            raise ValueError(f"Unknown evaluation_metric '{metric}'. Valid: {sorted(_VALID_SIMILARITY_METRICS)}")
        return v


EvaluatorDef = Annotated[
    BuiltinMetricDef | CodeEvaluatorDef | RemoteEvaluatorDef | OpenAIEvalDef,
    Field(discriminator="type"),
]


def make_builtin_evaluator_entries(
    metric_names: list[str] | None,
    *,
    judge_model: str | None = None,
    threshold: float | None = None,
    trajectory_match_type: str | None = None,
) -> list[BuiltinMetricDef]:
    metrics = metric_names if metric_names is not None else ["tool_trajectory_avg_score"]

    evaluators: list[BuiltinMetricDef] = []
    for name in metrics:
        evaluators.append(
            BuiltinMetricDef(
                name=name,
                judge_model=judge_model,
                threshold=threshold,
                trajectory_match_type=trajectory_match_type,
            )
        )
    return evaluators


class EvalParams(BaseModel):
    """Evaluation parameters independent of how traces are provided.

    Used by ``run_evaluation_from_traces`` for programmatic / API-driven
    evaluation.  ``EvalRunConfig`` inherits from this and adds file I/O fields.
    """

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")

    evaluators: list[EvaluatorDef] = Field(
        default_factory=lambda: [BuiltinMetricDef(name="tool_trajectory_avg_score")],
        description="Evaluator definitions, including built-in evaluators and custom evaluators.",
    )

    @field_validator("evaluators")
    @classmethod
    def _validate_evaluators(cls, v: list[EvaluatorDef]) -> list[EvaluatorDef]:
        if not v:
            raise ValueError("At least one evaluator is required.")
        duplicate_names = sorted(
            name for name, count in Counter(evaluator.name for evaluator in v).items() if count > 1
        )
        if duplicate_names:
            raise ValueError("Evaluator names must be globally unique. Duplicate names: " + ", ".join(duplicate_names))
        return v

    max_concurrent_traces: int = Field(
        default=10,
        ge=1,
        description="Maximum number of traces to evaluate concurrently.",
    )

    max_concurrent_evals: int = Field(
        default=5,
        ge=1,
        description="Maximum number of concurrent evaluator executions (for example LLM API calls).",
    )


class EvalRunConfig(EvalParams):
    """Full configuration for file-based evaluation runs."""

    trace_files: list[str] = Field(description="Paths to trace files (Jaeger or OTLP JSON, .json or .jsonl).")

    eval_set_file: str | None = Field(
        default=None,
        description="Path to a golden eval set JSON file (ADK EvalSet format).",
    )

    trace_format: str | None = Field(
        default=None,
        description=(
            "Optional explicit trace format override ('jaeger-json' or 'otlp-json'). "
            "Leave unset to auto-detect from file contents."
        ),
    )

    output_format: str = Field(
        default="table",
        description="Output format: 'table', 'json', or 'summary'.",
    )
