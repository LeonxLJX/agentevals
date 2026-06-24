"""Secret resolver framework tests.

Covers entry-point discovery and the builtins < entry points < programmatic
precedence chain (mirroring tests/run/test_sinks.py), the built-in env resolver,
the per-run ContextVar carrier, and resolve_credential_refs.
"""

from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import pytest

from agentevals.resolvers import (
    EnvSecretResolver,
    build_resolver,
    clear_resolver_plugin_registry,
    create_env_resolver,
    get_resolved_credential,
    register_resolver_factory,
    registered_resolver_kinds,
    reset_resolved_credentials,
    resolve_credential_refs,
    set_resolved_credentials,
)


@pytest.fixture
def isolated_resolver_plugins():
    """``register_resolver_factory`` is process-global; reset around plugin tests."""
    clear_resolver_plugin_registry()
    yield
    clear_resolver_plugin_registry()


class TestEnvResolver:
    def test_env_resolver_discovered_via_entry_point(self):
        assert "env" in registered_resolver_kinds()

    def test_create_env_resolver_returns_env_resolver(self):
        assert isinstance(create_env_resolver({"kind": "env"}), EnvSecretResolver)

    async def test_resolves_from_environment(self, monkeypatch):
        monkeypatch.setenv("AE_TEST_SECRET", "sk-from-env")
        ref = {"kind": "env", "name": "AE_TEST_SECRET"}
        assert await build_resolver(ref).resolve(ref) == "sk-from-env"

    async def test_missing_name_field_raises(self):
        with pytest.raises(ValueError, match="name"):
            await EnvSecretResolver().resolve({"kind": "env"})

    async def test_unset_variable_raises(self, monkeypatch):
        monkeypatch.delenv("AE_TEST_MISSING", raising=False)
        with pytest.raises(ValueError, match="not set"):
            await EnvSecretResolver().resolve({"kind": "env", "name": "AE_TEST_MISSING"})


class TestBuildResolver:
    def test_missing_kind_raises(self):
        with pytest.raises(ValueError, match="missing a 'kind'"):
            build_resolver({"name": "X"})

    def test_unknown_kind_raises_and_lists_available(self):
        with pytest.raises(ValueError, match="unknown secret resolver kind 'nope'") as exc:
            build_resolver({"kind": "nope"})
        assert "env" in str(exc.value)


class TestPluginPrecedence:
    async def test_programmatic_registration_overrides_entry_point(self, isolated_resolver_plugins):
        class Sentinel:
            async def resolve(self, ref):
                return "programmatic"

        register_resolver_factory("env", lambda _ref: Sentinel())
        resolver = build_resolver({"kind": "env"})
        assert isinstance(resolver, Sentinel)
        assert await resolver.resolve({"kind": "env"}) == "programmatic"

    def test_register_adds_new_kind(self, isolated_resolver_plugins):
        register_resolver_factory("custom", lambda _ref: MagicMock())
        assert "custom" in registered_resolver_kinds()


class TestEntryPointDiscovery:
    """Entry-point discovery without relying on packages installed in the test venv."""

    async def test_entry_point_resolver_resolves_kind(self, isolated_resolver_plugins):
        class FromEp:
            async def resolve(self, ref):
                return "from-entry-point"

        def factory(_ref):
            return FromEp()

        ep = MagicMock()
        ep.name = "from_ep"
        ep.load.return_value = factory

        with patch("agentevals.resolvers.entry_points", return_value=[ep]):
            resolver = build_resolver({"kind": "from_ep"})
        ep.load.assert_called_once_with()
        assert await resolver.resolve({"kind": "from_ep"}) == "from-entry-point"

    def test_entry_point_load_failure_skipped(self, isolated_resolver_plugins, caplog):
        ep = MagicMock()
        ep.name = "broken_pkg_resolver"
        ep.load.side_effect = ImportError("dist not installed")

        with patch("agentevals.resolvers.entry_points", return_value=[ep]), caplog.at_level(logging.ERROR):
            kinds = registered_resolver_kinds()
        assert "broken_pkg_resolver" not in kinds
        assert any("failed to load resolver entry point" in r.getMessage() for r in caplog.records)

    def test_non_callable_entry_point_skipped(self, isolated_resolver_plugins, caplog):
        ep = MagicMock()
        ep.name = "bad_export"
        ep.load.return_value = "not_callable"

        with patch("agentevals.resolvers.entry_points", return_value=[ep]), caplog.at_level(logging.WARNING):
            kinds = registered_resolver_kinds()
        assert "bad_export" not in kinds
        assert any("not callable" in r.getMessage() for r in caplog.records)


class TestResolvedCredentialContext:
    def test_get_returns_none_for_absent_key(self):
        token = set_resolved_credentials({"present": "v"})
        try:
            assert get_resolved_credential("present") == "v"
            assert get_resolved_credential("absent") is None
        finally:
            reset_resolved_credentials(token)

    async def test_resolve_credential_refs_maps_logical_names_to_values(self, monkeypatch):
        monkeypatch.setenv("AE_TEST_A", "val-a")
        monkeypatch.setenv("AE_TEST_B", "val-b")
        resolved = await resolve_credential_refs(
            {
                "a": {"kind": "env", "name": "AE_TEST_A"},
                "b": {"kind": "env", "name": "AE_TEST_B"},
            }
        )
        assert resolved == {"a": "val-a", "b": "val-b"}
