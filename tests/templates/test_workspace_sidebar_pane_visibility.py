#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The desktop sidebar offers each root-mounted pane to the right audience.

``tests/templates/test_every_pane_is_linkable.py`` reads SOURCE: it proves the
declaration in ``apps/infra/workspace_app/core_panes.py`` covers every pane the
URLconf mounts and that each entry carries a label and a visibility. This file
asserts the RENDERED consequence against a real response, because a complete
declaration wired up wrongly renders exactly like one that is ignored.

The three rules under test are not invented here — they are the ones the other
nav surfaces have carried all along:

    /chat/    everyone   mobile menu (global_header.html:818), mobile dock
                         (launcher.html:87) — no gate on either
    /console/ staff      mobile menu wraps it in {% if DEBUG or user.is_staff %}
                         (global_header.html:824); the mobile dock omits it
    /files/   everyone   mobile menu (global_header.html:830), mobile dock
                         (launcher.html:91) — no gate on either

The desktop sidebar was the one surface with no opinion, because until PR #626
it offered all three as ``<button data-pane=...>`` and never emitted an href at
all. Giving it anchors made the question real, and answering it "everyone" put
``href="/console/"`` on every regular user's page.

DEBUG is forced False so the staff gate reduces to ``user.is_staff`` — with the
dev default of DEBUG=True the gate is always open and proves nothing. This is
the same reasoning, and the same override, as
``tests/apps/apps_app/test_header_mobile_menu_gate.py``, whose regular-user
assertion is what caught the leak.

MARKERS ARE DERIVED FROM THE ROUTE, NEVER TYPED, for the reason that file spells
out at length: a hard-coded ``/workspace/console/`` went stale in 2026-07 and
broke the pair ASYMMETRICALLY — the positive half failed loudly, the negative
half kept passing, because a string that exists nowhere is absent from every
page. ``reverse()`` moves both halves together and raises if the name ever
disappears. Each marker is the full ``href="..."`` attribute rather than the
bare path: ``/console/`` is a substring of the unrelated ``/apps/console/``
route, and ``/files/`` of ``/apps/files/``-shaped paths.

Real Django test client, no mocks. One assertion per test (STX-TQ007).
"""

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse


def _href(url_name: str) -> bytes:
    """The pane's rendered ``href="..."``, straight from the router."""
    return b'href="' + reverse(url_name).encode() + b'"'


@override_settings(DEBUG=False)
class WorkspaceSidebarPaneVisibilityTest(TestCase):
    """Each core pane reaches the audience its declaration names."""

    @classmethod
    def setUpTestData(cls):
        cls.regular_user = User.objects.create_user(
            username="sidebar-regular-user",
            password="TestPass123!",  # pragma: allowlist secret
        )
        cls.staff_user = User.objects.create_user(
            username="sidebar-staff-user",
            password="TestPass123!",  # pragma: allowlist secret
            is_staff=True,
        )

    def test_regular_user_can_reach_chat_by_link(self):
        """The operator's ask: /chat/ must be findable, not pushState-only."""
        # Arrange
        self.client.force_login(self.regular_user)
        # Act
        resp = self.client.get("/")
        # Assert
        assert _href("pane-chat") in resp.content

    def test_regular_user_can_reach_files_by_link(self):
        # Arrange
        self.client.force_login(self.regular_user)
        # Act
        resp = self.client.get("/")
        # Assert
        assert _href("pane-files") in resp.content

    def test_regular_user_is_not_offered_console(self):
        """The leak PR #626 introduced, asserted at the surface that leaked."""
        # Arrange
        self.client.force_login(self.regular_user)
        # Act
        resp = self.client.get("/")
        # Assert
        assert _href("pane-console") not in resp.content

    def test_staff_user_is_offered_console(self):
        """Paired control: the gate opens, so the negative test means something."""
        # Arrange
        self.client.force_login(self.staff_user)
        # Act
        resp = self.client.get("/")
        # Assert
        assert _href("pane-console") in resp.content

    def test_staff_user_still_gets_chat(self):
        """Gating one pane must not have hidden the ungated ones from staff."""
        # Arrange
        self.client.force_login(self.staff_user)
        # Act
        resp = self.client.get("/")
        # Assert
        assert _href("pane-chat") in resp.content


if __name__ == "__main__":
    import os

    import pytest

    pytest.main([os.path.abspath(__file__)])

# EOF
