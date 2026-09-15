#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regression coverage for development template-tag module discovery."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from config import dev_autoreload


def test_templatetag_watch_includes_directory_metadata_and_python_modules(monkeypatch):
    """A new library changes a watched directory before it can be imported."""
    # Arrange
    app_path = Path("/workspace/example_app")
    sender = Mock()
    monkeypatch.setattr(
        dev_autoreload.django_apps,
        "get_app_configs",
        lambda: [SimpleNamespace(path=str(app_path))],
    )

    # Act
    dev_autoreload.watch_templatetag_paths(sender)

    # Assert
    watched = [call.args for call in sender.watch_dir.call_args_list]
    assert watched == [
        (app_path.parent, app_path.name),
        (app_path, "templatetags"),
        (app_path / "templatetags", "*.py"),
    ]


def test_templatetag_watcher_covers_every_installed_application(monkeypatch):
    """Hub and editable leaf apps receive the same discovery behavior."""
    # Arrange
    app_paths = [Path("/app/apps/hub_app"), Path("/editable/scitex_leaf")]
    sender = Mock()
    monkeypatch.setattr(
        dev_autoreload.django_apps,
        "get_app_configs",
        lambda: [SimpleNamespace(path=str(path)) for path in app_paths],
    )

    # Act
    dev_autoreload.watch_templatetag_paths(sender)

    # Assert
    watched = [call.args for call in sender.watch_dir.call_args_list]
    assert watched == [
        (app_paths[0].parent, app_paths[0].name),
        (app_paths[0], "templatetags"),
        (app_paths[0] / "templatetags", "*.py"),
        (app_paths[1].parent, app_paths[1].name),
        (app_paths[1], "templatetags"),
        (app_paths[1] / "templatetags", "*.py"),
    ]


def test_install_connects_one_stable_signal_receiver(monkeypatch):
    """Repeated settings imports cannot accumulate duplicate receivers."""
    # Arrange
    signal = Mock()
    monkeypatch.setattr(dev_autoreload, "autoreload_started", signal)

    # Act
    dev_autoreload.install_templatetag_autoreload()

    # Assert
    signal.connect.assert_called_once_with(
        dev_autoreload.watch_templatetag_paths,
        dispatch_uid="scitex-hub-dev-templatetag-autoreload",
    )


# EOF
