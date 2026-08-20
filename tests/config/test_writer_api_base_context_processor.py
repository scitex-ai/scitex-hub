#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/config/test_writer_api_base_context_processor.py
"""Tests for config.context_processors.writer_api_base (scitex-hub#146 Part B).

CONFIRMED BUG this processor fixes
-----------------------------------
``scitex_writer._django.views.editor_page`` / ``viewer_page`` render
``writer/{editor,viewer}.html`` without ever setting ``api_base`` in their
own context dict. The template falls back to ``{{ api_base|default:'/' }}``,
which is correct ONLY for scitex-writer's own standalone deployment (mounted
at the domain root). Hub mounts the same views under
``/apps/writer/{editor,viewer}-v2/`` and (scitex-hub#146 Part B)
``/<username>/<slug>/live/`` — with no context processor supplying
``api_base``, ``writer_app/frontend/src/api.ts``'s
``fetch(API_BASE + endpoint)`` calls silently targeted the wrong absolute
path (``/api/claims`` instead of ``/apps/writer/v2/api/claims``) and 404'd:
the editor/viewer shell rendered, but no claim, DAG, or manuscript data
ever loaded.

These are pure unit tests of the processor function against a bare
``RequestFactory`` request — no DB, no scitex-writer needed, since the
processor only inspects ``request.path``. One assertion per test
(STX-TQ007).
"""

from __future__ import annotations

from django.test import RequestFactory

from config.context_processors import writer_api_base


def test_editor_v2_path_resolves_the_v2_api_base():
    # Arrange
    request = RequestFactory().get("/apps/writer/editor-v2/")
    # Act
    context = writer_api_base(request)
    # Assert
    assert context["api_base"] == "/apps/writer/v2/"


def test_viewer_v2_path_resolves_the_v2_api_base():
    # Arrange
    request = RequestFactory().get("/apps/writer/viewer-v2/")
    # Act
    context = writer_api_base(request)
    # Assert
    assert context["api_base"] == "/apps/writer/v2/"


def test_public_live_viewer_path_resolves_its_own_v2_api_base():
    # Arrange
    request = RequestFactory().get("/alice/paper-demo/live/")
    # Act
    context = writer_api_base(request)
    # Assert
    assert context["api_base"] == "/alice/paper-demo/live/v2/"


def test_editor_and_live_api_base_do_not_collide():
    # Arrange: two requests of the different kinds this processor handles.
    editor_request = RequestFactory().get("/apps/writer/editor-v2/")
    live_request = RequestFactory().get("/bob/demo/live/")
    # Act: a copy-paste bug could make both branches resolve identically.
    editor_base = writer_api_base(editor_request)["api_base"]
    live_base = writer_api_base(live_request)["api_base"]
    # Assert
    assert editor_base != live_base


def test_unrelated_path_gets_no_api_base_key():
    # Arrange
    request = RequestFactory().get("/apps/scholar/")
    # Act
    context = writer_api_base(request)
    # Assert
    assert context == {}


if __name__ == "__main__":
    import os

    import pytest

    pytest.main([os.path.abspath(__file__)])
