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

import os
import warnings
from collections.abc import Iterator

import pytest

from config._env import (
    getenv_with_legacy_alias,
    require_env_with_legacy_alias,
)


class _EnvOverlay:
    """Real-os.environ overlay with snapshot/restore.

    Hand-rolled stand-in for `monkeypatch.setenv` / `delenv` (forbidden
    by PA-306). Mutates the live process env so production code reads
    the real environment, then restores the original values at teardown.
    """

    def __init__(self) -> None:
        self._snapshot: dict[str, str | None] = {}

    def set(self, key: str, value: str) -> None:
        if key not in self._snapshot:
            self._snapshot[key] = os.environ.get(key)
        os.environ[key] = value

    def unset(self, key: str) -> None:
        if key not in self._snapshot:
            self._snapshot[key] = os.environ.get(key)
        os.environ.pop(key, None)

    def restore(self) -> None:
        for key, original in self._snapshot.items():
            if original is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = original


@pytest.fixture
def env_overlay() -> Iterator[_EnvOverlay]:
    """Yield a real-environment overlay; restore os.environ at teardown."""
    overlay = _EnvOverlay()
    try:
        yield overlay
    finally:
        overlay.restore()


class TestGetenvWithLegacyAlias:
    """Direct getenv-with-alias semantics."""

    def test_hub_value_wins_when_both_set(self, env_overlay):
        """When both prefixes are set, the canonical HUB value is returned."""
        # Arrange
        env_overlay.set("SCITEX_HUB_DJANGO_SECRET_KEY", "hub-value")
        env_overlay.set("SCITEX_CLOUD_DJANGO_SECRET_KEY", "cloud-value")
        # Act
        value = getenv_with_legacy_alias("SCITEX_HUB_DJANGO_SECRET_KEY")
        # Assert
        assert value == "hub-value"

    def test_hub_value_wins_emits_no_deprecation_warning(self, env_overlay):
        """When both prefixes are set, no DeprecationWarning is emitted."""
        # Arrange
        env_overlay.set("SCITEX_HUB_DJANGO_SECRET_KEY", "hub-value")
        env_overlay.set("SCITEX_CLOUD_DJANGO_SECRET_KEY", "cloud-value")
        # Act
        with warnings.catch_warnings(record=True) as record:
            warnings.simplefilter("always")
            getenv_with_legacy_alias("SCITEX_HUB_DJANGO_SECRET_KEY")
        # Assert
        assert [w for w in record if issubclass(w.category, DeprecationWarning)] == []

    def test_cloud_alias_emits_deprecation_warning_when_hub_unset(self, env_overlay):
        """SCITEX_CLOUD_* triggers a DeprecationWarning when HUB_* is unset."""
        # Arrange
        env_overlay.unset("SCITEX_HUB_DJANGO_SECRET_KEY")
        env_overlay.set("SCITEX_CLOUD_DJANGO_SECRET_KEY", "abc")
        # Act / Assert
        # Assert
        with pytest.warns(DeprecationWarning, match="SCITEX_CLOUD_DJANGO_SECRET_KEY"):
            getenv_with_legacy_alias("SCITEX_HUB_DJANGO_SECRET_KEY")

    def test_cloud_alias_returns_legacy_value_when_hub_unset(self, env_overlay):
        """SCITEX_CLOUD_* value is what's returned when HUB_* is unset."""
        # Arrange
        env_overlay.unset("SCITEX_HUB_DJANGO_SECRET_KEY")
        env_overlay.set("SCITEX_CLOUD_DJANGO_SECRET_KEY", "abc")
        # Act
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            value = getenv_with_legacy_alias("SCITEX_HUB_DJANGO_SECRET_KEY")
        # Assert
        assert value == "abc"

    def test_default_returned_when_neither_prefix_set(self, env_overlay):
        """Default applies only when both canonical and legacy are absent."""
        # Arrange
        env_overlay.unset("SCITEX_HUB_SOMETHING")
        env_overlay.unset("SCITEX_CLOUD_SOMETHING")
        # Act
        value = getenv_with_legacy_alias("SCITEX_HUB_SOMETHING", "fallback")
        # Assert
        assert value == "fallback"

    def test_returns_none_when_no_default_and_both_unset(self, env_overlay):
        """No default, both prefixes unset -> None."""
        # Arrange
        env_overlay.unset("SCITEX_HUB_NOPE")
        env_overlay.unset("SCITEX_CLOUD_NOPE")
        # Act
        value = getenv_with_legacy_alias("SCITEX_HUB_NOPE")
        # Assert
        assert value is None

    def test_alias_is_one_directional_cloud_name_returns_none(self, env_overlay):
        """Passing a SCITEX_CLOUD_* name does NOT fall back to SCITEX_HUB_*.

        Direction is strictly HUB-canonical, CLOUD-legacy. The helper does
        not reverse-alias.
        """
        # Arrange
        env_overlay.set("SCITEX_HUB_X", "hub")
        env_overlay.unset("SCITEX_CLOUD_X")
        # Act
        value = getenv_with_legacy_alias("SCITEX_CLOUD_X")
        # Assert
        assert value is None


class TestRequireEnvWithLegacyAlias:
    """Hard-fail wrapper used by Django settings."""

    def test_raises_environment_error_when_both_unset(self, env_overlay):
        """Both names unset -> EnvironmentError mentioning the canonical name."""
        # Arrange
        env_overlay.unset("SCITEX_HUB_REQUIRED_FOO")
        env_overlay.unset("SCITEX_CLOUD_REQUIRED_FOO")
        # Act / Assert
        # Assert
        with pytest.raises(EnvironmentError, match="SCITEX_HUB_REQUIRED_FOO"):
            require_env_with_legacy_alias("SCITEX_HUB_REQUIRED_FOO")

    def test_accepts_legacy_alias_and_returns_value(self, env_overlay):
        """Legacy SCITEX_CLOUD_* set -> the value is returned."""
        # Arrange
        env_overlay.unset("SCITEX_HUB_REQUIRED_BAR")
        env_overlay.set("SCITEX_CLOUD_REQUIRED_BAR", "legacy-value")
        # Act
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            value = require_env_with_legacy_alias("SCITEX_HUB_REQUIRED_BAR")
        # Assert
        assert value == "legacy-value"

    def test_accepts_legacy_alias_emits_deprecation_warning(self, env_overlay):
        """Legacy SCITEX_CLOUD_* set -> a DeprecationWarning is emitted."""
        # Arrange
        env_overlay.unset("SCITEX_HUB_REQUIRED_BAR")
        env_overlay.set("SCITEX_CLOUD_REQUIRED_BAR", "legacy-value")
        # Act / Assert
        # Assert
        with pytest.warns(DeprecationWarning):
            require_env_with_legacy_alias("SCITEX_HUB_REQUIRED_BAR")


class TestSettingsModulesHonorTheAlias:
    """The alias layer only helps if the settings modules actually USE it.

    Regression guard: settings_dev used to re-read the secret key with a
    plain ``os.getenv("SCITEX_HUB_DJANGO_SECRET_KEY")`` AFTER star-importing
    settings_shared. That bypassed the alias, so a deployment exporting only
    the legacy ``SCITEX_CLOUD_DJANGO_SECRET_KEY`` (which is what the
    checked-in dev env file does) had its correctly-resolved value silently
    overwritten with ``None`` -- and Django refused to boot with
    "The SECRET_KEY setting must not be empty."

    The helper's own tests above all passed throughout; the defect was in the
    consumer. Hence this test imports the real settings module rather than
    the helper.
    """

    def _secret_key_from_settings(self, module: str, env: dict[str, str]) -> str:
        """Import a settings module in a subprocess and echo its SECRET_KEY.

        A subprocess is used because Django settings modules are import-time
        side-effecting and process-global; importing one in-process would
        leak into every later test.
        """
        import subprocess
        import sys
        from pathlib import Path

        repo_root = Path(__file__).resolve().parents[2]
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import importlib;"
                f"m = importlib.import_module('{module}');"
                "print(m.SECRET_KEY)",
            ],
            env=env,
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert result.returncode == 0, (
            f"{module} failed to import with only the legacy alias set.\n"
            f"stderr:\n{result.stderr}"
        )
        # settings_dev prints diagnostics (e.g. the redis-unavailable notice) to
        # stdout at import time, so the key is the LAST line, not the whole buffer.
        lines = [ln for ln in result.stdout.splitlines() if ln.strip()]
        assert lines, f"{module} printed nothing; stderr:\n{result.stderr}"
        return lines[-1].strip()

    def test_dev_settings_accept_the_legacy_secret_key_alias(self):
        """settings_dev boots when ONLY SCITEX_CLOUD_DJANGO_SECRET_KEY is set."""
        # Arrange
        env = dict(os.environ)
        env.pop("SCITEX_HUB_DJANGO_SECRET_KEY", None)
        env["SCITEX_CLOUD_DJANGO_SECRET_KEY"] = "legacy-only-value"
        env["SCITEX_HUB_USE_SQLITE_DEV"] = "1"
        env["PYTHONWARNINGS"] = "ignore::DeprecationWarning"
        # Act
        secret_key = self._secret_key_from_settings(
            "config.settings.settings_dev", env
        )
        # Assert
        assert secret_key == "legacy-only-value"


# EOF
