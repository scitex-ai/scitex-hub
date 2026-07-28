#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mobile hamburger menu hides developer items from ordinary users.

Operator (Telegram, 2026-07-21): narrow the hamburger for users and keep
developer-facing entries (Server Status / Keyboard Shortcuts / Console)
out of the way. They are gated behind ``{% if DEBUG or user.is_staff %}``
in templates/global_base_partials/global_header.html — the same gate the
header notification center already uses.

Console's menu link is UNIQUE to the mobile menu across every template,
so it is the clean signal for this gate (Server Status / Keyboard
Shortcuts also appear in the desktop header, so their bare strings cannot
distinguish the two surfaces). DEBUG is forced False so the gate reduces
to ``user.is_staff`` — with the dev default of DEBUG=True the gate is
always open and proves nothing.

THE MARKER IS DERIVED FROM THE ROUTE, NEVER TYPED. It was hard-coded as
``/workspace/console/`` until 2026-07-28, when the menu was repointed to
the real route (that path 404'd on prod). The hard-coded literal did not
merely go stale — it broke the pair ASYMMETRICALLY, which is the part
worth remembering:

  * the staff test failed LOUDLY (the new href no longer matched), but
  * the regular-user test kept PASSING, because it asserts the marker is
    ABSENT and a string that exists nowhere is absent from every page.

So the negative half silently became a gate that cannot fail — green for
a user whose menu leaked every developer item. Deriving the marker with
``reverse()`` makes that failure mode unreachable: a repoint moves both
halves together, and if the name ever disappears ``reverse`` raises
instead of quietly asserting nothing. The two tests also guard each
other — a meaningless marker would fail the staff test immediately.

Real Django test client, no mocks (same conventions as the sibling
launcher tests). One assertion per test (STX-TQ007).
"""

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse


@override_settings(DEBUG=False)
class MobileMenuDevItemGateTest(TestCase):
    """Console (a developer/power tool) is staff-only in the mobile menu."""

    @classmethod
    def setUpTestData(cls):
        cls.regular_user = User.objects.create_user(
            username="regular-user",
            password="TestPass123!",  # pragma: allowlist secret
        )
        cls.staff_user = User.objects.create_user(
            username="staff-user",
            password="TestPass123!",  # pragma: allowlist secret
            is_staff=True,
        )

    @classmethod
    def _console_href(cls):
        """The console pane's rendered ``href="..."``, straight from the router.

        The full attribute, not the bare path: ``reverse("pane-console")``
        is ``/console/``, which is a SUBSTRING of the unrelated and always
        present ``/apps/console/`` route (config/urls.py). Matching the bare
        path would make the regular-user assertion fail on a page whose
        mobile menu is correctly gated — a false red that would then get
        "fixed" by weakening the test. Anchoring on ``href="/console/"``
        cannot collide with ``href="/apps/console/"``.
        """
        return b'href="' + reverse("pane-console").encode() + b'"'

    def test_regular_user_menu_hides_console(self):
        # Arrange
        self.client.force_login(self.regular_user)
        # Act
        resp = self.client.get("/")
        # Assert
        assert self._console_href() not in resp.content

    def test_staff_user_menu_shows_console(self):
        # Arrange
        self.client.force_login(self.staff_user)
        # Act
        resp = self.client.get("/")
        # Assert
        assert self._console_href() in resp.content


if __name__ == "__main__":
    import os

    import pytest

    pytest.main([os.path.abspath(__file__)])

# EOF
