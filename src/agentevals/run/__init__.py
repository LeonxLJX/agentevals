"""Async run pipeline for ``POST /api/runs``.

Contents:
- :mod:`fetcher` resolves a run spec's ``target`` into a list of traces.
- :mod:`sinks` fan-out result delivery (built-ins plus setuptools plugins / :func:`~agentevals.run.sinks.register_sink_factory`).
- :mod:`service` is the synchronous control surface used by HTTP handlers.
- :mod:`worker` is the in-process loop that claims runs and drives the
  existing :func:`agentevals.runner.run_evaluation_from_traces` pipeline.
"""
