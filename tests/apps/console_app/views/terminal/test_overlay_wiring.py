#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for the flag-gated SIF+overlay wiring (DEFAULT OFF).

Covers, for the SIF+overlay migration (Increment 3):

1. Config flags ``APPTAINER_OVERLAY_ENABLED`` / ``OVERLAY_ROOT`` and
   their fail-safe defaults (only the literal string ``"true"`` enables).
2. The pure ``resolve_overlay_kwargs`` decision helper.
3. The load-bearing safety invariant: when the flag is DISABLED, every
   terminal command builder emits a command with NO ``--overlay`` and no
   ``--fakeroot`` (splatting an empty kwargs dict changes nothing, so the
   emitted command stays byte-identical to today's ``--writable-tmpfs``).

Everything is driven through the REAL env -> config -> command-builder
path (a yield-based fixture mutates ``os.environ`` and restores it; the
modules are reloaded so they re-read it). No mock/monkeypatch — the
tests exercise production wiring, not a patched stand-in (STX-NM001/002).

Flag-ON builder behavior is intentionally NOT exercised end-to-end: it
depends on per-user overlay images existing on the compute node, and the
flag stays OFF until the teardown (Inc 4) + promotion (Inc 5) increments
land. The enabled decision is covered at the pure ``resolve_overlay_kwargs``
boundary, so these tests do not couple to the installed
``scitex_container`` version.
"""

import importlib
import os
from pathlib import Path

import pytest

from apps.workspace.console_app.views.terminal._command_builder import (
    resolve_overlay_kwargs,
)

_ENABLE_ENV = "SCITEX_HUB_APPTAINER_OVERLAY_ENABLED"
_ROOT_ENV = "SCITEX_HUB_OVERLAY_ROOT"

# The two flags that must never appear while the feature is disabled.
_OVERLAY_FLAGS = ("--overlay", "--fakeroot")

# Representative, side-effect-free builder inputs (no filesystem/SLURM I/O
# happens — the builders only assemble argument lists / scripts).
_BUILDER_ARGS = dict(
    container_path="/opt/scitex/singularity/current-sandbox",
    username="alice",
    host_user_dir=Path("/opt/scitex/data/users/alice"),
    host_project_dir=Path("/opt/scitex/data/users/alice/projects/demo"),
    project_slug="demo",
)


@pytest.fixture
def env_setter():
    """Set real env vars for the test and restore them on teardown.

    Yields a ``set(key, value)`` callable; ``value=None`` unsets the key.
    The original values (including absence) are restored afterwards, so
    tests never leak overlay env into one another.
    """
    saved = {}

    def _set(key, value):
        if key not in saved:
            saved[key] = os.environ.get(key)
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value

    yield _set

    for key, original in saved.items():
        if original is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = original


def _reload_config():
    """Reload the config module so it re-reads the current environment."""
    import apps.workspace.console_app.views.terminal.config as cfg

    importlib.reload(cfg)
    return cfg


def _reload_command_builder():
    """Reload config + command builder so both re-read the current env."""
    import apps.workspace.console_app.views.terminal.config as cfg
    import apps.workspace.console_app.views.terminal._command_builder as cb

    importlib.reload(cfg)
    importlib.reload(cb)
    return cb


def _leaked_overlay_flags(command):
    """Return the overlay/fakeroot flags present in a built command.

    Works for both an argv ``list[str]`` (membership) and a shell-script
    ``str`` (substring) — either way an empty result means the disabled
    feature left no trace.
    """
    return [flag for flag in _OVERLAY_FLAGS if flag in command]


class TestApptainerOverlayConfig:
    """APPTAINER_OVERLAY_ENABLED / OVERLAY_ROOT resolution from env."""

    def test_absent_env_leaves_overlay_disabled(self, env_setter):
        # Arrange
        env_setter(_ENABLE_ENV, None)
        # Act
        cfg = _reload_config()
        # Assert
        assert cfg.APPTAINER_OVERLAY_ENABLED is False

    def test_absent_env_uses_default_overlay_root(self, env_setter):
        # Arrange
        env_setter(_ROOT_ENV, None)
        # Act
        cfg = _reload_config()
        # Assert
        assert cfg.OVERLAY_ROOT == "/opt/scitex/data/overlays"

    def test_lowercase_true_string_enables_overlay(self, env_setter):
        # Arrange
        env_setter(_ENABLE_ENV, "true")
        # Act
        cfg = _reload_config()
        # Assert
        assert cfg.APPTAINER_OVERLAY_ENABLED is True

    def test_uppercase_true_string_enables_overlay(self, env_setter):
        # Arrange
        env_setter(_ENABLE_ENV, "TRUE")
        # Act
        cfg = _reload_config()
        # Assert
        assert cfg.APPTAINER_OVERLAY_ENABLED is True

    @pytest.mark.parametrize("value", ["false", "False", "0", "1", "yes", "on", ""])
    def test_non_true_values_leave_overlay_disabled(self, env_setter, value):
        # Arrange
        env_setter(_ENABLE_ENV, value)
        # Act
        cfg = _reload_config()
        # Assert
        assert cfg.APPTAINER_OVERLAY_ENABLED is False

    def test_overlay_root_env_overrides_default(self, env_setter):
        # Arrange
        env_setter(_ROOT_ENV, "/custom/overlays")
        # Act
        cfg = _reload_config()
        # Assert
        assert cfg.OVERLAY_ROOT == "/custom/overlays"


class TestResolveOverlayKwargs:
    """The pure decision helper mapping the flag -> builder kwargs."""

    def test_disabled_flag_returns_empty_kwargs(self):
        # Arrange
        overlay_root = "/opt/scitex/data/overlays"
        # Act
        kwargs = resolve_overlay_kwargs("alice", enabled=False, overlay_root=overlay_root)
        # Assert
        assert kwargs == {}

    def test_enabled_flag_returns_overlay_path_and_fakeroot(self):
        # Arrange
        overlay_root = "/opt/scitex/data/overlays"
        # Act
        kwargs = resolve_overlay_kwargs("alice", enabled=True, overlay_root=overlay_root)
        # Assert
        assert kwargs == {
            "overlay_path": "/opt/scitex/data/overlays/alice.img",
            "fakeroot": True,
        }

    def test_enabled_flag_interpolates_username_and_root(self):
        # Arrange
        overlay_root = "/data/ov"
        # Act
        kwargs = resolve_overlay_kwargs("bob", enabled=True, overlay_root=overlay_root)
        # Assert
        assert kwargs == {"overlay_path": "/data/ov/bob.img", "fakeroot": True}


class TestBuildersOmitOverlayWhenDisabled:
    """Disabled flag => no overlay/fakeroot leaks into any builder output."""

    def test_apptainer_args_omit_overlay_when_disabled(self, env_setter):
        # Arrange
        env_setter(_ENABLE_ENV, None)
        cb = _reload_command_builder()
        # Act
        args = cb.build_apptainer_args(**_BUILDER_ARGS)
        # Assert
        assert _leaked_overlay_flags(args) == []

    def test_srun_cmd_omits_overlay_when_disabled(self, env_setter):
        # Arrange
        env_setter(_ENABLE_ENV, None)
        cb = _reload_command_builder()
        # Act
        cmd = cb.build_srun_cmd(**_BUILDER_ARGS)
        # Assert
        assert _leaked_overlay_flags(cmd) == []

    def test_instance_script_omits_overlay_when_disabled(self, env_setter):
        # Arrange
        env_setter(_ENABLE_ENV, None)
        cb = _reload_command_builder()
        # Act
        script = cb.build_instance_start_script_cmd(
            **_BUILDER_ARGS, instance_name="scitex-alice"
        )
        # Assert
        assert _leaked_overlay_flags(script) == []


if __name__ == "__main__":
    pytest.main([os.path.abspath(__file__)])
