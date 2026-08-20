#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/config/test_mounted_app_launcher_context_processor.py
"""Tests for config.context_processors.mounted_app_launcher (store back-link a11y).

CONFIRMED BUG this processor fixes
-----------------------------------
scitex-ui's ``standalone_shell.html`` renders a launcher back-link ONLY when
the context carries a ``launcher`` key (scitex-ui PR #162). Storage and
Cards are upstream leaf packages mounted at ``/apps/storage/`` /
``/apps/cards/`` whose views never set ``launcher`` — and below 768px every
workspace pane is ``display:none``, so scitex-hub measured /apps/storage/ at
390x844 with ZERO anchor elements on the page: nothing a visitor could tap
to leave. This processor supplies ``launcher`` from the request path alone,
so it reaches those upstream views without forking them.

These are pure unit tests of the processor function against a bare
``RequestFactory`` request — no DB, no scitex-ui/scitex-storage/scitex-cards
needed, since the processor only inspects ``request.path``. One assertion
per test (STX-TQ007).
"""

from __future__ import annotations

from django.test import RequestFactory

from config.context_processors import mounted_app_launcher


def test_storage_path_gets_a_launcher_back_to_the_store():
    # Arrange
    request = RequestFactory().get("/apps/storage/")
    # Act
    context = mounted_app_launcher(request)
    # Assert
    assert context["launcher"] == {"url": "/apps/store/", "label": "Back to Store"}


def test_cards_path_gets_a_launcher_back_to_the_store():
    # Arrange
    request = RequestFactory().get("/apps/cards/")
    # Act
    context = mounted_app_launcher(request)
    # Assert
    assert context["launcher"] == {"url": "/apps/store/", "label": "Back to Store"}


def test_writer_editor_v2_path_gets_a_launcher():
    # Arrange
    request = RequestFactory().get("/apps/writer/editor-v2/")
    # Act
    context = mounted_app_launcher(request)
    # Assert
    assert context["launcher"] == {"url": "/apps/store/", "label": "Back to Store"}


def test_writer_viewer_v2_path_gets_a_launcher():
    # Arrange
    request = RequestFactory().get("/apps/writer/viewer-v2/")
    # Act
    context = mounted_app_launcher(request)
    # Assert
    assert context["launcher"] == {"url": "/apps/store/", "label": "Back to Store"}


def test_public_live_viewer_path_gets_no_launcher():
    # Arrange: an anonymous reader of a published paper has no reason to be
    # routed to the SciTeX app store.
    request = RequestFactory().get("/alice/paper-demo/live/")
    # Act
    context = mounted_app_launcher(request)
    # Assert
    assert context == {}


def test_full_workspace_path_gets_no_launcher():
    # Arrange: hub's own full-workspace pages already carry the sidebar's
    # own navigation, so a second back-link would be redundant.
    request = RequestFactory().get("/apps/scholar/")
    # Act
    context = mounted_app_launcher(request)
    # Assert
    assert context == {}


def test_storage_and_scholar_do_not_collide():
    # Arrange: two requests, one in scope and one not.
    storage_request = RequestFactory().get("/apps/storage/")
    scholar_request = RequestFactory().get("/apps/scholar/")
    # Act: a scoping bug could make both branches resolve identically.
    storage_context = mounted_app_launcher(storage_request)
    scholar_context = mounted_app_launcher(scholar_request)
    # Assert
    assert storage_context != scholar_context


if __name__ == "__main__":
    import os

    import pytest

    pytest.main([os.path.abspath(__file__)])
