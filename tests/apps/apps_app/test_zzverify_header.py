#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ADVERSARIAL verification of the dead-project-selector deletion.

Independent of the branch's own test. Adds what that test omits:
  * an explicit 200 assertion (so a 500 error page cannot be the substrate)
  * BOTH visitor roles (the deleted block had per-role {% if %} branches, so a
    boundary error could surface in only one role)
  * the anonymous role
  * a POSITIVE assertion that the surviving live container is present
  * a NEGATIVE assertion that the dead container class is gone, matched in
    exact attribute form (class="header-project-selector") because
    "header-project-selector-inline" CONTAINS "header-project-selector" as a
    substring and a bare-substring check would be vacuous
  * a functional assertion that the selector region still carries its
    interactive content, so "renders at all" cannot pass for "region intact"

Designed to run RED against the pre-deletion template and GREEN after.
"""

from django.contrib.auth.models import User
from django.test import TestCase

SELECTOR_IDS = (
    "project-selector-toggle",
    "project-selector-text",
    "project-selector-dropdown",
)

LIVE_CONTAINER = b'class="header-project-selector-inline"'
DEAD_CONTAINER = b'class="header-project-selector"'


def id_attr(element_id):
    return 'id="{}"'.format(element_id).encode()


class _Base(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.regular = User.objects.create_user(
            username="verify-regular",
            password="TestPass123!",  # pragma: allowlist secret
        )
        cls.pool_visitor = User.objects.create_user(
            username="visitor-001",
            password="TestPass123!",  # pragma: allowlist secret
        )
        cls.readonly_visitor = User.objects.create_user(
            username="readonly-visitor",
            password="TestPass123!",  # pragma: allowlist secret
        )

    def fetch(self, who=None):
        if who is not None:
            self.client.force_login(who)
        return self.client.get("/")


class AuthenticatedRoleTest(_Base):
    def test_status_is_200(self):
        # Arrange
        who = self.regular
        # Act
        resp = self.fetch(who)
        # Assert
        assert resp.status_code == 200

    def test_toggle_id_exactly_once(self):
        # Arrange
        marker = id_attr("project-selector-toggle")
        # Act
        content = self.fetch(self.regular).content
        # Assert
        assert content.count(marker) == 1, content.count(marker)

    def test_text_id_exactly_once(self):
        # Arrange
        marker = id_attr("project-selector-text")
        # Act
        content = self.fetch(self.regular).content
        # Assert
        assert content.count(marker) == 1, content.count(marker)

    def test_dropdown_id_exactly_once(self):
        # Arrange
        marker = id_attr("project-selector-dropdown")
        # Act
        content = self.fetch(self.regular).content
        # Assert
        assert content.count(marker) == 1, content.count(marker)

    def test_live_inline_container_present(self):
        # Arrange
        marker = LIVE_CONTAINER
        # Act
        content = self.fetch(self.regular).content
        # Assert
        assert content.count(marker) == 1, content.count(marker)

    def test_dead_container_absent(self):
        # Arrange
        marker = DEAD_CONTAINER
        # Act
        content = self.fetch(self.regular).content
        # Assert
        assert content.count(marker) == 0, content.count(marker)

    def test_selector_region_still_functional(self):
        # Arrange
        marker = b"Create New Project"
        # Act
        content = self.fetch(self.regular).content
        # Assert
        assert content.count(marker) == 1, content.count(marker)


class PoolVisitorRoleTest(_Base):
    def test_status_is_200(self):
        # Arrange
        who = self.pool_visitor
        # Act
        resp = self.fetch(who)
        # Assert
        assert resp.status_code == 200

    def test_toggle_id_exactly_once(self):
        # Arrange
        marker = id_attr("project-selector-toggle")
        # Act
        content = self.fetch(self.pool_visitor).content
        # Assert
        assert content.count(marker) == 1, content.count(marker)

    def test_text_id_exactly_once(self):
        # Arrange
        marker = id_attr("project-selector-text")
        # Act
        content = self.fetch(self.pool_visitor).content
        # Assert
        assert content.count(marker) == 1, content.count(marker)

    def test_dropdown_id_exactly_once(self):
        # Arrange
        marker = id_attr("project-selector-dropdown")
        # Act
        content = self.fetch(self.pool_visitor).content
        # Assert
        assert content.count(marker) == 1, content.count(marker)

    def test_live_inline_container_present(self):
        # Arrange
        marker = LIVE_CONTAINER
        # Act
        content = self.fetch(self.pool_visitor).content
        # Assert
        assert content.count(marker) == 1, content.count(marker)

    def test_dead_container_absent(self):
        # Arrange
        marker = DEAD_CONTAINER
        # Act
        content = self.fetch(self.pool_visitor).content
        # Assert
        assert content.count(marker) == 0, content.count(marker)

    def test_visitor_signup_cta_present_in_selector(self):
        # Arrange
        marker = b"Sign up to save your work"
        # Act
        content = self.fetch(self.pool_visitor).content
        # Assert
        assert content.count(marker) == 1, content.count(marker)


class ReadonlyVisitorRoleTest(_Base):
    def test_status_is_200(self):
        # Arrange
        who = self.readonly_visitor
        # Act
        resp = self.fetch(who)
        # Assert
        assert resp.status_code == 200

    def test_toggle_id_exactly_once(self):
        # Arrange
        marker = id_attr("project-selector-toggle")
        # Act
        content = self.fetch(self.readonly_visitor).content
        # Assert
        assert content.count(marker) == 1, content.count(marker)

    def test_text_id_exactly_once(self):
        # Arrange
        marker = id_attr("project-selector-text")
        # Act
        content = self.fetch(self.readonly_visitor).content
        # Assert
        assert content.count(marker) == 1, content.count(marker)

    def test_dropdown_id_exactly_once(self):
        # Arrange
        marker = id_attr("project-selector-dropdown")
        # Act
        content = self.fetch(self.readonly_visitor).content
        # Assert
        assert content.count(marker) == 1, content.count(marker)

    def test_live_inline_container_present(self):
        # Arrange
        marker = LIVE_CONTAINER
        # Act
        content = self.fetch(self.readonly_visitor).content
        # Assert
        assert content.count(marker) == 1, content.count(marker)

    def test_dead_container_absent(self):
        # Arrange
        marker = DEAD_CONTAINER
        # Act
        content = self.fetch(self.readonly_visitor).content
        # Assert
        assert content.count(marker) == 0, content.count(marker)


class AnonymousRoleTest(_Base):
    def test_status_is_200(self):
        # Arrange
        who = None
        # Act
        resp = self.fetch(who)
        # Assert
        assert resp.status_code == 200

    def test_dead_container_absent(self):
        # Arrange
        marker = DEAD_CONTAINER
        # Act
        content = self.fetch(None).content
        # Assert
        assert content.count(marker) == 0, content.count(marker)

    def test_no_selector_id_is_duplicated(self):
        # Arrange
        expected_max = 1
        # Act
        content = self.fetch(None).content
        counts = {i: content.count(id_attr(i)) for i in SELECTOR_IDS}
        # Assert
        assert max(counts.values()) <= expected_max, counts


# EOF
