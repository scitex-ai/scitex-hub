#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mobile hamburger menu hides developer items from ordinary users.

Operator (Telegram, 2026-07-21): narrow the hamburger for users and keep
developer-facing entries (Server Status / Keyboard Shortcuts / Console)
out of the way. They are gated behind ``{% if DEBUG or user.is_staff %}``
in templates/global_base_partials/global_header.html — the same gate the
header notification center already uses.

Console's menu link (``/workspace/console/``) is UNIQUE to the mobile
menu across every template, so it is the clean signal for this gate
(Server Status / Keyboard Shortcuts also appear in the desktop header, so
their bare strings cannot distinguish the two surfaces). DEBUG is forced
False so the gate reduces to ``user.is_staff`` — with the dev default of
DEBUG=True the gate is always open and proves nothing.

Real Django test client, no mocks (same conventions as the sibling
launcher tests). One assertion per test (STX-TQ007).
"""

from django.contrib.auth.models import User
from django.test import TestCase, override_settings


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

    def test_regular_user_menu_hides_console(self):
        # Arrange
        self.client.force_login(self.regular_user)
        # Act
        resp = self.client.get("/")
        # Assert
        assert b"/workspace/console/" not in resp.content

    def test_staff_user_menu_shows_console(self):
        # Arrange
        self.client.force_login(self.staff_user)
        # Act
        resp = self.client.get("/")
        # Assert
        assert b"/workspace/console/" in resp.content


if __name__ == "__main__":
    import os

    import pytest

    pytest.main([os.path.abspath(__file__)])

# EOF
