#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for apps views and API endpoints.

All tests use the real Django test DB via django.test.TestCase. There are
no mocks — each test exercises a real HTTP round-trip through the Django
test client against the real ORM. Assertions use bare `assert` (rather
than `self.assertEqual`) so the SciTeX linter (STX-TQ001) recognises
them as assertion calls; the behaviour is identical for TestCase.
"""

import json

from django.contrib.auth.models import User
from django.test import TestCase

from apps.workspace.apps_app.models import (
    AppsModule,
    ModuleInstallation,
    ModuleReview,
    ModuleStar,
)


class AppsBrowseTest(TestCase):
    """Tests for the browse page."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="browse-user",
            password="TestPass123!",  # pragma: allowlist secret
        )
        cls.module = AppsModule.objects.create(
            module_name="t-browse",
            short_description="LaTeX editor.",
            category="writing",
            is_builtin=True,
            visibility="public",
        )

    def test_browse_page_returns_200(self):
        # Arrange
        url = "/apps/store/"
        # Act
        resp = self.client.get(url)
        # Assert
        assert resp.status_code == 200

    def test_browse_page_with_category_filter_returns_200(self):
        # Arrange
        url = "/apps/store/?category=writing"
        # Act
        resp = self.client.get(url)
        # Assert
        assert resp.status_code == 200

    def test_browse_page_with_search_query_returns_200(self):
        # Arrange
        url = "/apps/store/?q=t-browse"
        # Act
        resp = self.client.get(url)
        # Assert
        assert resp.status_code == 200


class AppsDetailTest(TestCase):
    """Tests for the detail page."""

    @classmethod
    def setUpTestData(cls):
        cls.module = AppsModule.objects.create(
            module_name="t-detail",
            short_description="Literature manager.",
            category="reference",
            visibility="public",
        )

    def test_detail_page_existing_module_returns_200(self):
        # Arrange
        url = "/apps/store/t-detail/"
        # Act
        resp = self.client.get(url)
        # Assert
        assert resp.status_code == 200

    def test_detail_page_nonexistent_module_returns_404(self):
        # Arrange
        url = "/apps/store/nonexistent/"
        # Act
        resp = self.client.get(url)
        # Assert
        assert resp.status_code == 404


class AppsInstallTest(TestCase):
    """Tests for install/uninstall/toggle APIs."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="install-user",
            password="TestPass123!",  # pragma: allowlist secret
        )
        cls.module = AppsModule.objects.create(
            module_name="t-install",
            category="visualization",
            visibility="public",
        )
        cls.builtin = AppsModule.objects.create(
            module_name="t-builtin",
            category="writing",
            is_builtin=True,
            visibility="public",
        )

    def setUp(self):
        self.client.login(
            username="install-user",
            password="TestPass123!",  # pragma: allowlist secret
        )

    def test_install_endpoint_returns_200(self):
        # Arrange
        url = "/apps/store/api/t-install/install/"
        # Act
        resp = self.client.post(url)
        # Assert
        assert resp.status_code == 200

    def test_install_response_body_reports_success_true(self):
        # Arrange
        url = "/apps/store/api/t-install/install/"
        # Act
        resp = self.client.post(url)
        # Assert
        assert resp.json()["success"] is True

    def test_install_persists_module_installation_row(self):
        # Arrange
        url = "/apps/store/api/t-install/install/"
        # Act
        self.client.post(url)
        # Assert
        assert ModuleInstallation.objects.filter(
            user=self.user, module=self.module
        ).exists()

    def test_double_install_returns_400(self):
        # Arrange
        url = "/apps/store/api/t-install/install/"
        self.client.post(url)
        # Act
        resp = self.client.post(url)
        # Assert
        assert resp.status_code == 400

    def test_uninstall_endpoint_returns_200(self):
        # Arrange
        ModuleInstallation.objects.create(user=self.user, module=self.module)
        url = "/apps/store/api/t-install/uninstall/"
        # Act
        resp = self.client.post(url)
        # Assert
        assert resp.status_code == 200

    def test_uninstall_removes_module_installation_row(self):
        # Arrange
        ModuleInstallation.objects.create(user=self.user, module=self.module)
        url = "/apps/store/api/t-install/uninstall/"
        # Act
        self.client.post(url)
        # Assert
        assert not ModuleInstallation.objects.filter(
            user=self.user, module=self.module
        ).exists()

    def test_uninstall_builtin_module_returns_400(self):
        # Arrange
        ModuleInstallation.objects.create(user=self.user, module=self.builtin)
        url = "/apps/store/api/t-builtin/uninstall/"
        # Act
        resp = self.client.post(url)
        # Assert
        assert resp.status_code == 400

    def test_uninstall_builtin_error_message_mentions_builtin(self):
        # Arrange
        ModuleInstallation.objects.create(user=self.user, module=self.builtin)
        url = "/apps/store/api/t-builtin/uninstall/"
        # Act
        resp = self.client.post(url)
        # Assert
        assert "Built-in" in resp.json()["error"]

    def test_toggle_disables_an_enabled_installation(self):
        # Arrange
        ModuleInstallation.objects.create(
            user=self.user, module=self.module, is_enabled=True
        )
        url = "/apps/store/api/t-install/toggle/"
        # Act
        resp = self.client.post(url)
        # Assert
        assert resp.json()["is_enabled"] is False

    def test_toggle_twice_returns_to_enabled(self):
        # Arrange
        ModuleInstallation.objects.create(
            user=self.user, module=self.module, is_enabled=True
        )
        url = "/apps/store/api/t-install/toggle/"
        self.client.post(url)
        # Act
        resp = self.client.post(url)
        # Assert
        assert resp.json()["is_enabled"] is True


class AppsStarTest(TestCase):
    """Tests for star/unstar APIs."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="star-user",
            password="TestPass123!",  # pragma: allowlist secret
        )
        cls.module = AppsModule.objects.create(
            module_name="t-star",
            category="utility",
            visibility="public",
        )

    def setUp(self):
        self.client.login(
            username="star-user",
            password="TestPass123!",  # pragma: allowlist secret
        )

    def test_star_endpoint_returns_200(self):
        # Arrange
        url = "/apps/store/api/t-star/star/"
        # Act
        resp = self.client.post(url)
        # Assert
        assert resp.status_code == 200

    def test_star_increments_star_count_to_one(self):
        # Arrange
        url = "/apps/store/api/t-star/star/"
        # Act
        resp = self.client.post(url)
        # Assert
        assert resp.json()["star_count"] == 1

    def test_double_star_returns_400(self):
        # Arrange
        url = "/apps/store/api/t-star/star/"
        self.client.post(url)
        # Act
        resp = self.client.post(url)
        # Assert
        assert resp.status_code == 400

    def test_unstar_endpoint_returns_200(self):
        # Arrange
        ModuleStar.objects.create(user=self.user, module=self.module)
        url = "/apps/store/api/t-star/unstar/"
        # Act
        resp = self.client.post(url)
        # Assert
        assert resp.status_code == 200

    def test_unstar_decrements_star_count_to_zero(self):
        # Arrange
        ModuleStar.objects.create(user=self.user, module=self.module)
        url = "/apps/store/api/t-star/unstar/"
        # Act
        resp = self.client.post(url)
        # Assert
        assert resp.json()["star_count"] == 0


class AppsReviewTest(TestCase):
    """Tests for review API."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="review-user",
            password="TestPass123!",  # pragma: allowlist secret
        )
        cls.module = AppsModule.objects.create(
            module_name="t-review",
            category="reference",
            visibility="public",
        )

    def setUp(self):
        self.client.login(
            username="review-user",
            password="TestPass123!",  # pragma: allowlist secret
        )

    def test_create_review_endpoint_returns_200(self):
        # Arrange
        url = "/apps/store/api/t-review/review/"
        body = json.dumps({"rating": 5, "title": "Excellent", "body": "Love it."})
        # Act
        resp = self.client.post(url, data=body, content_type="application/json")
        # Assert
        assert resp.status_code == 200

    def test_create_review_response_reports_success_true(self):
        # Arrange
        url = "/apps/store/api/t-review/review/"
        body = json.dumps({"rating": 5, "title": "Excellent", "body": "Love it."})
        # Act
        resp = self.client.post(url, data=body, content_type="application/json")
        # Assert
        assert resp.json()["success"] is True

    def test_create_review_response_reports_created_true(self):
        # Arrange
        url = "/apps/store/api/t-review/review/"
        body = json.dumps({"rating": 5, "title": "Excellent", "body": "Love it."})
        # Act
        resp = self.client.post(url, data=body, content_type="application/json")
        # Assert
        assert resp.json()["created"] is True

    def test_update_existing_review_endpoint_returns_200(self):
        # Arrange
        ModuleReview.objects.create(
            user=self.user, module=self.module, rating=3, title="OK"
        )
        url = "/apps/store/api/t-review/review/"
        body = json.dumps({"rating": 5, "title": "Better now"})
        # Act
        resp = self.client.post(url, data=body, content_type="application/json")
        # Assert
        assert resp.status_code == 200

    def test_update_existing_review_response_reports_created_false(self):
        # Arrange
        ModuleReview.objects.create(
            user=self.user, module=self.module, rating=3, title="OK"
        )
        url = "/apps/store/api/t-review/review/"
        body = json.dumps({"rating": 5, "title": "Better now"})
        # Act
        resp = self.client.post(url, data=body, content_type="application/json")
        # Assert
        assert resp.json()["created"] is False  # Updated, not created

    def test_invalid_rating_returns_400(self):
        # Arrange
        url = "/apps/store/api/t-review/review/"
        body = json.dumps({"rating": 0, "title": "Bad"})
        # Act
        resp = self.client.post(url, data=body, content_type="application/json")
        # Assert
        assert resp.status_code == 400

    def test_invalid_json_body_returns_400(self):
        # Arrange
        url = "/apps/store/api/t-review/review/"
        # Act
        resp = self.client.post(url, data="not json", content_type="application/json")
        # Assert
        assert resp.status_code == 400


class AppsReorderTest(TestCase):
    """Tests for reorder API."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="reorder-user",
            password="TestPass123!",  # pragma: allowlist secret
        )
        cls.mod_a = AppsModule.objects.create(
            module_name="t-reorder-a", category="other", visibility="public"
        )
        cls.mod_b = AppsModule.objects.create(
            module_name="t-reorder-b", category="other", visibility="public"
        )

    def setUp(self):
        self.client.login(
            username="reorder-user",
            password="TestPass123!",  # pragma: allowlist secret
        )
        ModuleInstallation.objects.create(
            user=self.user, module=self.mod_a, tab_order=10
        )
        ModuleInstallation.objects.create(
            user=self.user, module=self.mod_b, tab_order=20
        )

    def test_reorder_endpoint_returns_200(self):
        # Arrange
        url = "/apps/store/api/reorder/"
        body = json.dumps({"order": ["t-reorder-b", "t-reorder-a"]})
        # Act
        resp = self.client.post(url, data=body, content_type="application/json")
        # Assert
        assert resp.status_code == 200

    def test_reorder_swaps_tab_order_so_a_comes_after_b(self):
        # Arrange
        url = "/apps/store/api/reorder/"
        body = json.dumps({"order": ["t-reorder-b", "t-reorder-a"]})
        # Act
        self.client.post(url, data=body, content_type="application/json")
        inst_a = ModuleInstallation.objects.get(user=self.user, module=self.mod_a)
        inst_b = ModuleInstallation.objects.get(user=self.user, module=self.mod_b)
        # Assert
        assert inst_a.tab_order > inst_b.tab_order


class AppsAuthTest(TestCase):
    """Tests that API endpoints require authentication."""

    @classmethod
    def setUpTestData(cls):
        cls.module = AppsModule.objects.create(
            module_name="t-auth", category="other", visibility="public"
        )

    def test_install_requires_login_redirects_to_login(self):
        # Arrange
        url = "/apps/store/api/t-auth/install/"
        # Act
        resp = self.client.post(url)
        # Assert
        assert resp.status_code == 302  # Redirect to login

    def test_star_requires_login_redirects_to_login(self):
        # Arrange
        url = "/apps/store/api/t-auth/star/"
        # Act
        resp = self.client.post(url)
        # Assert
        assert resp.status_code == 302

    def test_review_requires_login_redirects_to_login(self):
        # Arrange
        url = "/apps/store/api/t-auth/review/"
        # Act
        resp = self.client.post(url)
        # Assert
        assert resp.status_code == 302


# EOF
