#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for apps models."""

from decimal import Decimal

from django.contrib.auth.models import User
from django.db import IntegrityError
from django.test import TestCase

from apps.workspace.apps_app.models import (
    AppsModule,
    ModuleInstallation,
    ModuleReview,
    ModuleStar,
    ModuleVersion,
)


class AppsModuleTest(TestCase):
    """Tests for AppsModule model."""

    @classmethod
    def setUpTestData(cls):
        cls.author = User.objects.create_user(
            username="test-author",
            password="TestPass123!",  # pragma: allowlist secret
        )
        cls.module = AppsModule.objects.create(
            module_name="test-module",
            author=cls.author,
            short_description="A test module.",
            category="utility",
            is_builtin=False,
            visibility="public",
        )

    def test_str(self):
        self.assertEqual(str(self.module), "test-module (utility)")

    def test_unique_module_name(self):
        with self.assertRaises(IntegrityError):
            AppsModule.objects.create(
                module_name="test-module",
                category="other",
            )

    def test_update_stats_empty(self):
        self.module.update_stats()
        self.assertEqual(self.module.star_count, 0)
        self.assertEqual(self.module.install_count, 0)
        self.assertEqual(self.module.avg_rating, Decimal("0"))


class ModuleVersionTest(TestCase):
    """Tests for ModuleVersion model."""

    @classmethod
    def setUpTestData(cls):
        cls.module = AppsModule.objects.create(module_name="ver-test", category="other")

    def test_create_version(self):
        v = ModuleVersion.objects.create(
            module=self.module, version="1.0.0", changelog="Initial.", is_stable=True
        )
        self.assertEqual(str(v), "ver-test v1.0.0")

    def test_unique_module_version(self):
        ModuleVersion.objects.create(module=self.module, version="1.0.0")
        with self.assertRaises(IntegrityError):
            ModuleVersion.objects.create(module=self.module, version="1.0.0")


class ModuleInstallationTest(TestCase):
    """Tests for ModuleInstallation model."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="test-installer",
            password="TestPass123!",  # pragma: allowlist secret
        )
        cls.module = AppsModule.objects.create(
            module_name="install-test", category="utility"
        )

    def test_install(self):
        inst = ModuleInstallation.objects.create(
            user=self.user, module=self.module, is_enabled=True, tab_order=10
        )
        self.assertTrue(inst.is_enabled)
        self.assertEqual(inst.tab_order, 10)

    def test_unique_user_module(self):
        ModuleInstallation.objects.create(user=self.user, module=self.module)
        with self.assertRaises(IntegrityError):
            ModuleInstallation.objects.create(user=self.user, module=self.module)

    def test_toggle(self):
        inst = ModuleInstallation.objects.create(
            user=self.user, module=self.module, is_enabled=True
        )
        inst.is_enabled = False
        inst.save()
        inst.refresh_from_db()
        self.assertFalse(inst.is_enabled)


class ModuleStarTest(TestCase):
    """Tests for ModuleStar model."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="test-starrer",
            password="TestPass123!",  # pragma: allowlist secret
        )
        cls.module = AppsModule.objects.create(
            module_name="star-test", category="other"
        )

    def test_star(self):
        star = ModuleStar.objects.create(user=self.user, module=self.module)
        self.assertEqual(str(star), "test-starrer starred star-test")

    def test_unique_star(self):
        ModuleStar.objects.create(user=self.user, module=self.module)
        with self.assertRaises(IntegrityError):
            ModuleStar.objects.create(user=self.user, module=self.module)

    def test_update_stats_after_star(self):
        ModuleStar.objects.create(user=self.user, module=self.module)
        self.module.update_stats()
        self.assertEqual(self.module.star_count, 1)


class ModuleReviewTest(TestCase):
    """Tests for ModuleReview model."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="test-reviewer",
            password="TestPass123!",  # pragma: allowlist secret
        )
        cls.module = AppsModule.objects.create(
            module_name="review-test", category="other"
        )

    def test_create_review(self):
        review = ModuleReview.objects.create(
            user=self.user,
            module=self.module,
            rating=4,
            title="Great module",
            body="Works well.",
        )
        self.assertIn("4/5", str(review))

    def test_unique_review_per_user(self):
        ModuleReview.objects.create(
            user=self.user, module=self.module, rating=5, title="Good"
        )
        with self.assertRaises(IntegrityError):
            ModuleReview.objects.create(
                user=self.user, module=self.module, rating=3, title="Changed mind"
            )

    def test_avg_rating_update(self):
        user2 = User.objects.create_user(
            username="reviewer2",
            password="TestPass123!",  # pragma: allowlist secret
        )
        ModuleReview.objects.create(
            user=self.user, module=self.module, rating=4, title="Good"
        )
        ModuleReview.objects.create(
            user=user2, module=self.module, rating=2, title="OK"
        )
        self.module.update_stats()
        self.assertEqual(self.module.avg_rating, Decimal("3.0"))


# EOF
