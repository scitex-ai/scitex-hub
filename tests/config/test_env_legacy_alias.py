# -*- coding: utf-8 -*-
# File: tests/config/test_env_legacy_alias.py
"""Tests for the SCITEX_CLOUD_* -> SCITEX_HUB_* env-var alias layer.

Background: ADR-0001 renamed the operator-facing env-var prefix from
``SCITEX_CLOUD_*`` to ``SCITEX_HUB_*`` (commit d38d6894). Existing
deployments may still export the legacy prefix; the alias layer in
``config/_env.py`` accepts the legacy name with a ``DeprecationWarning``
(no silent fallback, per CLAUDE.md).
"""
from __future__ import annotations

import warnings

import pytest

from config._env import (
    getenv_with_legacy_alias,
    require_env_with_legacy_alias,
)


class TestGetenvWithLegacyAlias:
    """Direct getenv-with-alias semantics."""

    def test_hub_value_preferred_when_both_set(self, monkeypatch):
        """If both prefixes are set, the canonical HUB value wins (no warning)."""
        monkeypatch.setenv("SCITEX_HUB_DJANGO_SECRET_KEY", "hub-value")
        monkeypatch.setenv("SCITEX_CLOUD_DJANGO_SECRET_KEY", "cloud-value")
        with warnings.catch_warnings(record=True) as record:
            warnings.simplefilter("always")
            value = getenv_with_legacy_alias("SCITEX_HUB_DJANGO_SECRET_KEY")
        assert value == "hub-value"
        # No DeprecationWarning should fire when HUB is set.
        deprecation_warnings = [
            w for w in record if issubclass(w.category, DeprecationWarning)
        ]
        assert deprecation_warnings == []

    def test_cloud_alias_used_when_hub_unset_emits_warning(self, monkeypatch):
        """SCITEX_CLOUD_* is read when SCITEX_HUB_* is unset, with warning.

        This is the headline behaviour requested by the operator:
        existing deployments that still export SCITEX_CLOUD_DJANGO_SECRET_KEY
        keep working, but we surface the deprecation explicitly.
        """
        monkeypatch.delenv("SCITEX_HUB_DJANGO_SECRET_KEY", raising=False)
        monkeypatch.setenv("SCITEX_CLOUD_DJANGO_SECRET_KEY", "abc")
        with pytest.warns(DeprecationWarning, match="SCITEX_CLOUD_DJANGO_SECRET_KEY"):
            value = getenv_with_legacy_alias("SCITEX_HUB_DJANGO_SECRET_KEY")
        assert value == "abc"

    def test_default_returned_when_neither_set(self, monkeypatch):
        """Default applies only when both canonical and legacy are absent."""
        monkeypatch.delenv("SCITEX_HUB_SOMETHING", raising=False)
        monkeypatch.delenv("SCITEX_CLOUD_SOMETHING", raising=False)
        assert (
            getenv_with_legacy_alias("SCITEX_HUB_SOMETHING", "fallback") == "fallback"
        )

    def test_none_returned_when_no_default(self, monkeypatch):
        monkeypatch.delenv("SCITEX_HUB_NOPE", raising=False)
        monkeypatch.delenv("SCITEX_CLOUD_NOPE", raising=False)
        assert getenv_with_legacy_alias("SCITEX_HUB_NOPE") is None

    def test_alias_is_one_directional(self, monkeypatch):
        """Passing a SCITEX_CLOUD_* name does not fall back to SCITEX_HUB_*.

        Direction is strictly HUB-canonical, CLOUD-legacy. Callers should
        only ever pass the canonical HUB name; the helper does NOT try to
        synthesize HUB from a CLOUD-name read.
        """
        monkeypatch.setenv("SCITEX_HUB_X", "hub")
        monkeypatch.delenv("SCITEX_CLOUD_X", raising=False)
        # Asking directly for the legacy name returns None (it's unset),
        # NOT the HUB value — the helper does not reverse-alias.
        assert getenv_with_legacy_alias("SCITEX_CLOUD_X") is None


class TestRequireEnvWithLegacyAlias:
    """Hard-fail wrapper used by Django settings."""

    def test_raises_when_both_unset(self, monkeypatch):
        monkeypatch.delenv("SCITEX_HUB_REQUIRED_FOO", raising=False)
        monkeypatch.delenv("SCITEX_CLOUD_REQUIRED_FOO", raising=False)
        with pytest.raises(EnvironmentError, match="SCITEX_HUB_REQUIRED_FOO"):
            require_env_with_legacy_alias("SCITEX_HUB_REQUIRED_FOO")

    def test_accepts_legacy_alias_with_warning(self, monkeypatch):
        monkeypatch.delenv("SCITEX_HUB_REQUIRED_BAR", raising=False)
        monkeypatch.setenv("SCITEX_CLOUD_REQUIRED_BAR", "legacy-value")
        with pytest.warns(DeprecationWarning):
            value = require_env_with_legacy_alias("SCITEX_HUB_REQUIRED_BAR")
        assert value == "legacy-value"


# EOF
