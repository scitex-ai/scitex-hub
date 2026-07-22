#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/custom/test_cloud_helpers.py

"""Tests for the module-level cloud helpers on ``scitex_hub``.

These wrap :class:`scitex_hub.CloudClient` and are re-exported by the umbrella
as ``stx.cloud.get_context``, ``stx.cloud.eval_js``, ``stx.cloud.ui_action``.
"""

import pytest

import scitex_hub


class _FakeClient:
    """Records the kwargs it was constructed with and the calls it received."""

    last_init_kwargs = None
    last_call = None

    def __init__(self, **kwargs):
        type(self).last_init_kwargs = kwargs

    def get_context(self, page):
        type(self).last_call = ("get_context", page)
        return {"page": page, "username": "tester"}

    def eval_js(self, code, timeout):
        type(self).last_call = ("eval_js", code, timeout)
        return {"code": code, "timeout": timeout}

    def ui_action(self, steps, delay_ms):
        type(self).last_call = ("ui_action", steps, delay_ms)
        return {"steps": steps, "delay_ms": delay_ms}


@pytest.fixture
def fake_client():
    """Swap the real CloudClient for a recording fake; restore on teardown."""
    original = scitex_hub.CloudClient
    _FakeClient.last_init_kwargs = None
    _FakeClient.last_call = None
    scitex_hub.CloudClient = _FakeClient
    try:
        yield _FakeClient
    finally:
        scitex_hub.CloudClient = original


def test_get_context_is_importable_from_scitex_hub():
    # Arrange
    # (no setup — importing the public symbol is the behaviour under test)
    # Act
    from scitex_hub import get_context

    # Assert
    assert callable(get_context)


def test_eval_js_is_importable_from_scitex_hub():
    # Arrange
    # Act
    from scitex_hub import eval_js

    # Assert
    assert callable(eval_js)


def test_ui_action_is_importable_from_scitex_hub():
    # Arrange
    # Act
    from scitex_hub import ui_action

    # Assert
    assert callable(ui_action)


def test_get_context_listed_in_dunder_all():
    # Arrange
    exported = scitex_hub.__all__
    # Act
    present = "get_context" in exported
    # Assert
    assert present is True


def test_eval_js_listed_in_dunder_all():
    # Arrange
    exported = scitex_hub.__all__
    # Act
    present = "eval_js" in exported
    # Assert
    assert present is True


def test_ui_action_listed_in_dunder_all():
    # Arrange
    exported = scitex_hub.__all__
    # Act
    present = "ui_action" in exported
    # Assert
    assert present is True


def test_get_context_returns_client_result(fake_client):
    # Arrange
    page = "dashboard"
    # Act
    result = scitex_hub.get_context(page)
    # Assert
    assert result == {"page": "dashboard", "username": "tester"}


def test_get_context_forwards_kwargs_to_client(fake_client):
    # Arrange
    # Act
    scitex_hub.get_context("dashboard", base_url="http://x")
    # Assert
    assert fake_client.last_init_kwargs == {"base_url": "http://x"}


def test_get_context_defaults_to_current_page(fake_client):
    # Arrange
    # Act
    scitex_hub.get_context()
    # Assert
    assert fake_client.last_call == ("get_context", "")


def test_eval_js_passes_code_and_timeout(fake_client):
    # Arrange
    # Act
    scitex_hub.eval_js("document.title", timeout=30)
    # Assert
    assert fake_client.last_call == ("eval_js", "document.title", 30)


def test_eval_js_default_timeout_is_ten(fake_client):
    # Arrange
    # Act
    scitex_hub.eval_js("1+1")
    # Assert
    assert fake_client.last_call == ("eval_js", "1+1", 10)


def test_ui_action_passes_steps_and_delay(fake_client):
    # Arrange
    steps = [{"action": "click", "selector": "#go"}]
    # Act
    scitex_hub.ui_action(steps, delay_ms=200)
    # Assert
    assert fake_client.last_call == ("ui_action", steps, 200)


def test_ui_action_default_delay_is_nine_hundred(fake_client):
    # Arrange
    # Act
    scitex_hub.ui_action([])
    # Assert
    assert fake_client.last_call == ("ui_action", [], 900)


# EOF
