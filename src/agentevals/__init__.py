"""agentevals: Standalone CLI to evaluate agent traces using ADK's scoring framework."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("agentevals-cli")
except PackageNotFoundError:
    __version__ = "0.0.0-dev"


def __getattr__(name):
    if name == "AgentEvals":
        from .sdk import AgentEvals

        return AgentEvals
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
