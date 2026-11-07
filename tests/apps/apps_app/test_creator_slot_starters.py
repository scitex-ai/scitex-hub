#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SDK slot previews the SDK starter set (operator screenshot fix)."""

import pytest

from apps.workspace.apps_app.views.launcher import _creator_starter_previews

scitex_sdk = pytest.importorskip(
    "scitex_sdk.creator", reason="starter previews need the SDK creator package"
)


def test_previews_mirror_the_sdk_starter_set():
    from scitex_sdk.creator import STARTERS

    previews = _creator_starter_previews()
    assert [(p["icon"], p["label"]) for p in previews] == [
        (s.icon, s.label) for s in STARTERS
    ]
    assert len(previews) == 4


def test_previews_degrade_to_empty_without_the_sdk(monkeypatch):
    import builtins

    real_import = builtins.__import__

    def refuse_sdk(name, *args, **kwargs):
        if name == "scitex_sdk.creator" or name.startswith("scitex_sdk.creator."):
            raise ImportError("simulated absent SDK")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", refuse_sdk)
    assert _creator_starter_previews() == []
