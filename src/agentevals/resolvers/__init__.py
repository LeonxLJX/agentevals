"""Secret resolvers — a generic, pluggable layer for resolving secret references.

A host attaches *secret references* to a run (``RunSpec.credential_refs``); each
reference is a ``dict`` with a ``kind`` plus kind-specific locator fields. At run
time the worker resolves every reference once to its secret value and stashes the
``logical-name -> value`` map in a :class:`contextvars.ContextVar` scoped to that
run's asyncio task. Consumers (e.g. judge construction) read the value they need
with no ``os.environ`` mutation and no shared state across concurrently running
evaluations.

This layer is deliberately consumer-agnostic: a resolver turns a reference into a
secret value and nothing more. How that value is used — which provider it
authenticates, what base URL it pairs with — is the consumer's concern, configured
where the consumer is built (for judges, on the evaluator definition).

**Plugins:** third-party packages declare setuptools entry points in group
``agentevals.secret_resolvers`` (entry **name** = ``kind`` string; **value** =
``module:factory`` callable ``factory(spec: dict) -> SecretResolver``). The
zero-dependency ``env`` resolver ships with agentevals through this same group so
the discovery path is exercised in OSS. Hosts may replace any kind via
:func:`register_resolver_factory` (highest precedence).

Tests may call :func:`clear_resolver_plugin_registry` to drop programmatic
registrations.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Callable
from contextvars import ContextVar, Token
from importlib.metadata import entry_points
from typing import Any, Protocol, cast

logger = logging.getLogger(__name__)

SECRET_RESOLVER_ENTRY_POINT_GROUP = "agentevals.secret_resolvers"


class SecretResolver(Protocol):
    async def resolve(self, ref: dict[str, Any]) -> str: ...


SecretResolverFactory = Callable[[dict[str, Any]], SecretResolver]

_PLUGIN_FACTORIES: dict[str, SecretResolverFactory] = {}


class EnvSecretResolver:
    """Resolve ``{"kind": "env", "name": "OPENAI_API_KEY"}`` from ``os.environ``."""

    async def resolve(self, ref: dict[str, Any]) -> str:
        name = ref.get("name")
        if not name:
            raise ValueError("env secret reference requires a 'name' field")
        value = os.environ.get(name)
        if value is None:
            raise ValueError(f"environment variable {name!r} is not set")
        return value


def create_env_resolver(spec: dict[str, Any]) -> EnvSecretResolver:
    return EnvSecretResolver()


def register_resolver_factory(kind: str, factory: SecretResolverFactory) -> None:
    """Register or replace the factory for ``kind`` (overrides built-ins and entry points).

    Call during process startup before run workers consume specs. The factory receives
    the full reference dict (including ``kind``) and returns a :class:`SecretResolver`.
    """
    _PLUGIN_FACTORIES[kind] = factory


def clear_resolver_plugin_registry() -> None:
    """Drop all registrations from :func:`register_resolver_factory` (for tests)."""
    _PLUGIN_FACTORIES.clear()


def _builtin_factories() -> dict[str, SecretResolverFactory]:
    """No hardcoded built-ins: ``env`` ships via the entry-point group."""
    return {}


def _merge_resolver_factories() -> dict[str, SecretResolverFactory]:
    """Built-ins, then entry points (no built-in shadowing), then programmatic overrides."""
    merged: dict[str, SecretResolverFactory] = dict(_builtin_factories())
    eps = entry_points(group=SECRET_RESOLVER_ENTRY_POINT_GROUP)
    for ep in eps:
        if ep.name in merged:
            logger.debug("skipping resolver entry point %r; built-in kind takes precedence", ep.name)
            continue
        try:
            loaded = ep.load()
            if not callable(loaded):
                logger.warning("resolver entry point %r is not callable; skipping", ep.name)
                continue
            merged[ep.name] = cast(SecretResolverFactory, loaded)
        except Exception:
            logger.exception("failed to load resolver entry point %r", ep.name)
    merged.update(_PLUGIN_FACTORIES)
    return merged


def registered_resolver_kinds() -> tuple[str, ...]:
    """Sorted resolver ``kind`` strings that would resolve if :func:`build_resolver` ran now.

    Includes built-ins, successfully loaded setuptools entry points for group
    :data:`SECRET_RESOLVER_ENTRY_POINT_GROUP`, and registrations from
    :func:`register_resolver_factory`.
    """
    return tuple(sorted(_merge_resolver_factories().keys()))


def build_resolver(ref: dict[str, Any]) -> SecretResolver:
    """Construct the :class:`SecretResolver` for a reference's ``kind``.

    Factory lookup starts from built-ins, adds setuptools entry points (group
    ``agentevals.secret_resolvers``) for ``kind`` names not already built-in, then
    applies :func:`register_resolver_factory` registrations, which override any prior
    factory for the same ``kind``.
    """
    kind = ref.get("kind")
    if not kind:
        raise ValueError("secret reference is missing a 'kind' field")
    factories = _merge_resolver_factories()
    factory = factories.get(kind)
    if factory is None:
        raise ValueError(
            f"unknown secret resolver kind '{kind}'. Available: {', '.join(sorted(factories)) or '(none)'}"
        )
    return factory(ref)


async def resolve_credential_refs(refs: dict[str, dict[str, Any]]) -> dict[str, str]:
    """Resolve every ``logical-name -> reference`` entry to its secret value.

    Each resolver reads only its own kind-specific locator fields. Any non-locator
    fields a host puts on a reference are ignored here; consumer-specific config
    belongs with the consumer (for judges, on the evaluator definition).
    """
    resolved: dict[str, str] = {}
    for logical_name, ref in refs.items():
        resolver = build_resolver(ref)
        resolved[logical_name] = await resolver.resolve(ref)
    return resolved


_RESOLVED: ContextVar[dict[str, str] | None] = ContextVar("agentevals_resolved_credentials", default=None)


def set_resolved_credentials(mapping: dict[str, str]) -> Token:
    """Scope a ``logical-name -> secret value`` map to the current asyncio task. Returns a reset token."""
    return _RESOLVED.set(mapping)


def reset_resolved_credentials(token: Token) -> None:
    _RESOLVED.reset(token)


def get_resolved_credential(logical_name: str) -> str | None:
    """Look up a secret value resolved for the current run, or ``None`` if absent."""
    mapping = _RESOLVED.get()
    if not mapping:
        return None
    return mapping.get(logical_name)
