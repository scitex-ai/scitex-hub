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
needed. The processor resolves mounted prefixes from the plugin registry
(``plugin_mount_prefixes``), so every test here runs under a SYNTHETIC
mount table via the ``PLUGIN_MOUNT_TABLE_OVERRIDE`` setting — the same seam
``tests/apps/apps_app/test_plugin_mount_guards.py`` drives the guard with.
Results therefore do not depend on which optional plugin packages happen to
be installed in the environment (Storage, for example, is an optional
plugin mount since 082a0c51f, not a built-in). One assertion
per test (STX-TQ007).
"""

from __future__ import annotations

import pytest
from django.test import RequestFactory

from config.context_processors import mounted_app_launcher

#: Storage- and cards-shaped standalone mounts. Storage stands in for any
#: optional plugin mount: the point under test is the processor's scoping,
#: not which plugins this environment installed.
SYNTHETIC_MOUNT_TABLE = [
    ("/apps/storage/", "Storage", {"login_required": True}),
    ("/apps/cards/", "Cards", {"login_required": True}),
]


@pytest.fixture(autouse=True)
def _synthetic_plugin_mounts(settings):
    settings.PLUGIN_MOUNT_TABLE_OVERRIDE = SYNTHETIC_MOUNT_TABLE


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


def _signed_in(request):
    request.user = type("SignedIn", (), {"is_authenticated": True})()
    return request


def test_cards_path_with_the_site_dock_gets_no_launcher():
    # Arrange: signed-in pages get the site dock, which is already the way out.
    request = _signed_in(RequestFactory().get("/apps/cards/chat/"))
    # Act
    context = mounted_app_launcher(request)
    # Assert
    assert context == {}


def test_embedded_cards_page_keeps_its_launcher():
    # Arrange: ?embed=1 renders no dock, so the back-link must stay.
    request = _signed_in(RequestFactory().get("/apps/cards/?embed=1"))
    # Act
    context = mounted_app_launcher(request)
    # Assert
    assert "launcher" in context


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
