#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for marketplace views and API endpoints."""

import json

from django.contrib.auth.models import User
from django.test import TestCase

from apps.marketplace_app.models import (
    MarketplaceModule,
    ModuleInstallation,
    ModuleReview,
    ModuleStar,
)


class MarketplaceBrowseTest(TestCase):
    """Tests for the browse page."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="browse-user",
            password="TestPass123!",  # pragma: allowlist secret
        )
        cls.module = MarketplaceModule.objects.create(
            module_name="t-browse",
            short_description="LaTeX editor.",
            category="writing",
            is_builtin=True,
            visibility="public",
        )

    def test_browse_page_200(self):
        resp = self.client.get("/marketplace/")
        self.assertEqual(resp.status_code, 200)

    def test_browse_with_category_filter(self):
        resp = self.client.get("/marketplace/?category=writing")
        self.assertEqual(resp.status_code, 200)

    def test_browse_with_search(self):
        resp = self.client.get("/marketplace/?q=t-browse")
        self.assertEqual(resp.status_code, 200)


class MarketplaceDetailTest(TestCase):
    """Tests for the detail page."""

    @classmethod
    def setUpTestData(cls):
        cls.module = MarketplaceModule.objects.create(
            module_name="t-detail",
            short_description="Literature manager.",
            category="reference",
            visibility="public",
        )

    def test_detail_page_200(self):
        resp = self.client.get("/marketplace/t-detail/")
        self.assertEqual(resp.status_code, 200)

    def test_detail_page_404(self):
        resp = self.client.get("/marketplace/nonexistent/")
        self.assertEqual(resp.status_code, 404)


class MarketplaceInstallTest(TestCase):
    """Tests for install/uninstall/toggle APIs."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="install-user",
            password="TestPass123!",  # pragma: allowlist secret
        )
        cls.module = MarketplaceModule.objects.create(
            module_name="t-install",
            category="visualization",
            visibility="public",
        )
        cls.builtin = MarketplaceModule.objects.create(
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

    def test_install(self):
        resp = self.client.post("/marketplace/api/t-install/install/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["success"])
        self.assertTrue(
            ModuleInstallation.objects.filter(
                user=self.user, module=self.module
            ).exists()
        )

    def test_double_install(self):
        self.client.post("/marketplace/api/t-install/install/")
        resp = self.client.post("/marketplace/api/t-install/install/")
        self.assertEqual(resp.status_code, 400)

    def test_uninstall(self):
        ModuleInstallation.objects.create(user=self.user, module=self.module)
        resp = self.client.post("/marketplace/api/t-install/uninstall/")
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(
            ModuleInstallation.objects.filter(
                user=self.user, module=self.module
            ).exists()
        )

    def test_uninstall_builtin_blocked(self):
        ModuleInstallation.objects.create(user=self.user, module=self.builtin)
        resp = self.client.post("/marketplace/api/t-builtin/uninstall/")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Built-in", resp.json()["error"])

    def test_toggle(self):
        ModuleInstallation.objects.create(
            user=self.user, module=self.module, is_enabled=True
        )
        resp = self.client.post("/marketplace/api/t-install/toggle/")
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.json()["is_enabled"])

        resp = self.client.post("/marketplace/api/t-install/toggle/")
        self.assertTrue(resp.json()["is_enabled"])


class MarketplaceStarTest(TestCase):
    """Tests for star/unstar APIs."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="star-user",
            password="TestPass123!",  # pragma: allowlist secret
        )
        cls.module = MarketplaceModule.objects.create(
            module_name="t-star",
            category="utility",
            visibility="public",
        )

    def setUp(self):
        self.client.login(
            username="star-user",
            password="TestPass123!",  # pragma: allowlist secret
        )

    def test_star(self):
        resp = self.client.post("/marketplace/api/t-star/star/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["star_count"], 1)

    def test_double_star(self):
        self.client.post("/marketplace/api/t-star/star/")
        resp = self.client.post("/marketplace/api/t-star/star/")
        self.assertEqual(resp.status_code, 400)

    def test_unstar(self):
        ModuleStar.objects.create(user=self.user, module=self.module)
        resp = self.client.post("/marketplace/api/t-star/unstar/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["star_count"], 0)


class MarketplaceReviewTest(TestCase):
    """Tests for review API."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="review-user",
            password="TestPass123!",  # pragma: allowlist secret
        )
        cls.module = MarketplaceModule.objects.create(
            module_name="t-review",
            category="reference",
            visibility="public",
        )

    def setUp(self):
        self.client.login(
            username="review-user",
            password="TestPass123!",  # pragma: allowlist secret
        )

    def test_create_review(self):
        resp = self.client.post(
            "/marketplace/api/t-review/review/",
            data=json.dumps({"rating": 5, "title": "Excellent", "body": "Love it."}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["success"])
        self.assertTrue(data["created"])

    def test_update_review(self):
        ModuleReview.objects.create(
            user=self.user, module=self.module, rating=3, title="OK"
        )
        resp = self.client.post(
            "/marketplace/api/t-review/review/",
            data=json.dumps({"rating": 5, "title": "Better now"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.json()["created"])  # Updated, not created

    def test_invalid_rating(self):
        resp = self.client.post(
            "/marketplace/api/t-review/review/",
            data=json.dumps({"rating": 0, "title": "Bad"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_invalid_json(self):
        resp = self.client.post(
            "/marketplace/api/t-review/review/",
            data="not json",
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)


class MarketplaceReorderTest(TestCase):
    """Tests for reorder API."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="reorder-user",
            password="TestPass123!",  # pragma: allowlist secret
        )
        cls.mod_a = MarketplaceModule.objects.create(
            module_name="t-reorder-a", category="other", visibility="public"
        )
        cls.mod_b = MarketplaceModule.objects.create(
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

    def test_reorder(self):
        resp = self.client.post(
            "/marketplace/api/reorder/",
            data=json.dumps({"order": ["t-reorder-b", "t-reorder-a"]}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        inst_a = ModuleInstallation.objects.get(user=self.user, module=self.mod_a)
        inst_b = ModuleInstallation.objects.get(user=self.user, module=self.mod_b)
        self.assertGreater(inst_a.tab_order, inst_b.tab_order)


class MarketplaceAuthTest(TestCase):
    """Tests that API endpoints require authentication."""

    @classmethod
    def setUpTestData(cls):
        cls.module = MarketplaceModule.objects.create(
            module_name="t-auth", category="other", visibility="public"
        )

    def test_install_requires_login(self):
        resp = self.client.post("/marketplace/api/t-auth/install/")
        self.assertEqual(resp.status_code, 302)  # Redirect to login

    def test_star_requires_login(self):
        resp = self.client.post("/marketplace/api/t-auth/star/")
        self.assertEqual(resp.status_code, 302)

    def test_review_requires_login(self):
        resp = self.client.post("/marketplace/api/t-auth/review/")
        self.assertEqual(resp.status_code, 302)


# EOF
