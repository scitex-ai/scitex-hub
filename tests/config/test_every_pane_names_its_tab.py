#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Every mounted workspace pane must be able to name its own browser tab.

THE DEFECT, screenshotted by the operator on 2026-08-16. The tab for
https://scitex.ai/chat/ read

    default-project — SciTeX

naming only the project, never the app — while /apps/writer/, /apps/scholar/
and every other app named itself. config/urls.py mounts three panes at the
ROOT, dispatched through root_dispatch with a `pane` kwarg:

    path("chat/",    root_dispatch, name="pane-chat",    kwargs={"pane": "chat"})
    path("console/", root_dispatch, name="pane-console", kwargs={"pane": "console"})
    path("files/",   root_dispatch, name="pane-files",   kwargs={"pane": "editor"})

None of the three appeared in PATH_LABELS, so app_for_path() returned None
and page_title() fell back to the detail alone.

WHY A DERIVED TEST AND NOT THREE ASSERTIONS. PATH_LABELS is an allowlist
maintained by hand, and this is the second time this session that a
hand-maintained prefix list has silently swallowed a real route — #618 was
the same shape, where /tokushoho/ was classified as a username because it
was missing from _NON_USER_PREFIXES. Asserting "/chat/ has a label" fixes
today's instance and lets the next pane fail exactly as silently.

So the panes are DERIVED from the URLconf. A fourth pane added tomorrow
without a label fails here, naming itself in the failure message. That is
the property worth guarding: the two lists cannot drift apart, which is
precisely what branding.py's own comment already warns about for the
/apps/ prefixes ("keep the two in step").
"""

from __future__ import annotations

import pytest
from django.urls import get_resolver
from django.urls.resolvers import URLPattern

from config.branding import app_for_path


def _mounted_panes() -> list[tuple[str, str]]:
    """Return (route, url_name) for every root-mounted workspace pane.

    Identified by carrying a ``pane`` kwarg, which is how config/urls.py
    marks them — not by matching on names, which would drift.
    """
    panes = []
    for pattern in get_resolver().url_patterns:
        if not isinstance(pattern, URLPattern):
            continue
        if "pane" not in (pattern.default_args or {}):
            continue
        route = getattr(pattern.pattern, "_route", "")
        # Skip parameterised variants like "chat/<uuid:session_token>/" —
        # the bare prefix is what names the tab.
        if "<" in route:
            continue
        panes.append(("/" + route, pattern.name or "<unnamed>"))
    return panes


class TestEveryPaneNamesItsTab:
    def test_the_urlconf_actually_exposes_panes(self):
        """Vacuity check: an empty sweep would make every test below pass."""
        # Arrange
        panes = _mounted_panes()

        # Act
        count = len(panes)

        # Assert
        assert count > 0, "found no pane routes — the derivation is broken"

    @pytest.mark.guards(
        defect=(
            "root-mounted panes (/chat/, /console/, /files/) were absent from "
            "PATH_LABELS, so app_for_path returned None and the browser tab "
            "named only the project instead of the app"
        )
    )
    def test_every_mounted_pane_has_a_tab_label(self):
        # Arrange
        panes = _mounted_panes()

        # Act
        unlabelled = [
            f"{route} ({name})" for route, name in panes if app_for_path(route) is None
        ]

        # Assert
        assert unlabelled == [], (
            "these panes cannot name their own tab — add them to "
            f"config.branding.PANE_NAMES: {unlabelled}"
        )

    @pytest.mark.guards(
        defect=(
            "the /chat/ tab read 'default-project — SciTeX', naming the "
            "project but never the app, because /chat/ had no label"
        )
    )
    def test_chat_is_named_chat(self):
        # Arrange
        path = "/chat/"

        # Act
        label = app_for_path(path)

        # Assert
        assert label == "Chat"

    def test_a_labelled_app_is_still_resolved(self):
        """Positive control: the sweep is not passing because nothing matches."""
        # Arrange
        path = "/apps/writer/"

        # Act
        label = app_for_path(path)

        # Assert
        assert label == "Writer"

    def test_an_unmounted_path_is_still_unlabelled(self):
        """Negative control: app_for_path has not become a yes-machine."""
        # Arrange
        path = "/definitely-not-an-app/"

        # Act
        label = app_for_path(path)

        # Assert
        assert label is None
