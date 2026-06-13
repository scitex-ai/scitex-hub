#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for apps models.

All tests use the real Django test DB. Assertions use bare `assert` or
`with pytest.raises(...)` (not `self.assertEqual` / `self.assertRaises`)
so the SciTeX linter (STX-TQ001) recognises them as assertion calls;
behaviour is identical for django.test.TestCase. Multi-assertion tests
have been split into one-behaviour-per-test pairs.
"""

from decimal import Decimal

import pytest
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


class AppsModuleStrTest(TestCase):
    """`AppsModule.__str__` rendering."""

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

    def test_str_formats_as_name_and_category(self):
        # Arrange
        expected = "test-module (utility)"
        # Act
        actual = str(self.module)
        # Assert
        assert actual == expected


class AppsModuleUniqueModuleNameTest(TestCase):
    """`module_name` uniqueness constraint."""

    @classmethod
    def setUpTestData(cls):
        cls.module = AppsModule.objects.create(
            module_name="test-module-unique",
            category="utility",
        )

    def test_duplicate_module_name_raises_integrity_error(self):
        # Arrange
        duplicate_name = "test-module-unique"
        # Act / Assert
        # Assert
        with pytest.raises(IntegrityError):
            AppsModule.objects.create(
                module_name=duplicate_name,
                category="other",
            )


class AppsModuleUpdateStatsEmptyTest(TestCase):
    """`update_stats()` on a freshly-created module with no install/review/star."""

    @classmethod
    def setUpTestData(cls):
        cls.module = AppsModule.objects.create(
            module_name="test-module-stats-empty",
            category="utility",
        )

    def test_update_stats_sets_star_count_to_zero(self):
        # Arrange
        # (fresh module, no stars)
        # Act
        self.module.update_stats()
        # Assert
        assert self.module.star_count == 0

    def test_update_stats_sets_install_count_to_zero(self):
        # Arrange
        # (fresh module, no installs)
        # Act
        self.module.update_stats()
        # Assert
        assert self.module.install_count == 0

    def test_update_stats_sets_avg_rating_to_zero_decimal(self):
        # Arrange
        # (fresh module, no reviews)
        # Act
        self.module.update_stats()
        # Assert
        assert self.module.avg_rating == Decimal("0")


class ModuleVersionCreateTest(TestCase):
    """`ModuleVersion.__str__` rendering."""

    @classmethod
    def setUpTestData(cls):
        cls.module = AppsModule.objects.create(module_name="ver-test", category="other")

    def test_str_formats_as_module_name_v_version(self):
        # Arrange
        v = ModuleVersion.objects.create(
            module=self.module,
            version="1.0.0",
            changelog="Initial.",
            is_stable=True,
        )
        # Act
        actual = str(v)
        # Assert
        assert actual == "ver-test v1.0.0"


class ModuleVersionUniqueModuleVersionTest(TestCase):
    """`(module, version)` uniqueness constraint on ModuleVersion."""

    @classmethod
    def setUpTestData(cls):
        cls.module = AppsModule.objects.create(
            module_name="ver-test-unique", category="other"
        )

    def test_duplicate_module_version_raises_integrity_error(self):
        # Arrange
        ModuleVersion.objects.create(module=self.module, version="1.0.0")
        # Act / Assert
        # Assert
        with pytest.raises(IntegrityError):
            ModuleVersion.objects.create(module=self.module, version="1.0.0")


class ModuleInstallationInstallTest(TestCase):
    """`ModuleInstallation` create / refresh / toggle round-trips."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="test-installer",
            password="TestPass123!",  # pragma: allowlist secret
        )
        cls.module = AppsModule.objects.create(
            module_name="install-test", category="utility"
        )

    def test_install_persists_is_enabled_true(self):
        # Arrange / Act
        # Act
        inst = ModuleInstallation.objects.create(
            user=self.user, module=self.module, is_enabled=True, tab_order=10
        )
        # Assert
        assert inst.is_enabled is True

    def test_install_persists_tab_order_value(self):
        # Arrange / Act
        # Act
        inst = ModuleInstallation.objects.create(
            user=self.user,
            module=self.module,
            is_enabled=True,
            tab_order=10,
        )
        # Assert
        assert inst.tab_order == 10


class ModuleInstallationUniqueUserModuleTest(TestCase):
    """`(user, module)` uniqueness constraint on ModuleInstallation."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="test-installer-unique",
            password="TestPass123!",  # pragma: allowlist secret
        )
        cls.module = AppsModule.objects.create(
            module_name="install-test-unique", category="utility"
        )

    def test_duplicate_user_module_raises_integrity_error(self):
        # Arrange
        ModuleInstallation.objects.create(user=self.user, module=self.module)
        # Act / Assert
        # Assert
        with pytest.raises(IntegrityError):
            ModuleInstallation.objects.create(user=self.user, module=self.module)


class ModuleInstallationToggleTest(TestCase):
    """`is_enabled` field round-trip on toggle."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="test-toggler",
            password="TestPass123!",  # pragma: allowlist secret
        )
        cls.module = AppsModule.objects.create(
            module_name="toggle-test", category="utility"
        )

    def test_toggle_off_persists_to_db(self):
        # Arrange
        inst = ModuleInstallation.objects.create(
            user=self.user, module=self.module, is_enabled=True
        )
        # Act
        inst.is_enabled = False
        inst.save()
        inst.refresh_from_db()
        # Assert
        assert inst.is_enabled is False


class ModuleStarStrTest(TestCase):
    """`ModuleStar.__str__` rendering."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="test-starrer",
            password="TestPass123!",  # pragma: allowlist secret
        )
        cls.module = AppsModule.objects.create(
            module_name="star-test", category="other"
        )

    def test_str_formats_as_user_starred_module(self):
        # Arrange
        star = ModuleStar.objects.create(user=self.user, module=self.module)
        # Act
        actual = str(star)
        # Assert
        assert actual == "test-starrer starred star-test"


class ModuleStarUniqueTest(TestCase):
    """`(user, module)` uniqueness constraint on ModuleStar."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="test-starrer-unique",
            password="TestPass123!",  # pragma: allowlist secret
        )
        cls.module = AppsModule.objects.create(
            module_name="star-test-unique", category="other"
        )

    def test_duplicate_user_module_star_raises_integrity_error(self):
        # Arrange
        ModuleStar.objects.create(user=self.user, module=self.module)
        # Act / Assert
        # Assert
        with pytest.raises(IntegrityError):
            ModuleStar.objects.create(user=self.user, module=self.module)


class ModuleStarUpdateStatsTest(TestCase):
    """`update_stats()` reflects a freshly-created star."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="test-star-stats",
            password="TestPass123!",  # pragma: allowlist secret
        )
        cls.module = AppsModule.objects.create(
            module_name="star-stats-test", category="other"
        )

    def test_update_stats_sets_star_count_to_one_after_a_star(self):
        # Arrange
        ModuleStar.objects.create(user=self.user, module=self.module)
        # Act
        self.module.update_stats()
        # Assert
        assert self.module.star_count == 1


class ModuleReviewCreateTest(TestCase):
    """`ModuleReview.__str__` rendering includes the rating."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="test-reviewer",
            password="TestPass123!",  # pragma: allowlist secret
        )
        cls.module = AppsModule.objects.create(
            module_name="review-test", category="other"
        )

    def test_str_includes_rating_fraction(self):
        # Arrange
        review = ModuleReview.objects.create(
            user=self.user,
            module=self.module,
            rating=4,
            title="Great module",
            body="Works well.",
        )
        # Act
        actual = str(review)
        # Assert
        assert "4/5" in actual


class ModuleReviewUniquePerUserTest(TestCase):
    """`(user, module)` uniqueness constraint on ModuleReview."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="test-reviewer-unique",
            password="TestPass123!",  # pragma: allowlist secret
        )
        cls.module = AppsModule.objects.create(
            module_name="review-test-unique", category="other"
        )

    def test_duplicate_user_module_review_raises_integrity_error(self):
        # Arrange
        ModuleReview.objects.create(
            user=self.user, module=self.module, rating=5, title="Good"
        )
        # Act / Assert
        # Assert
        with pytest.raises(IntegrityError):
            ModuleReview.objects.create(
                user=self.user,
                module=self.module,
                rating=3,
                title="Changed mind",
            )


class ModuleReviewAvgRatingTest(TestCase):
    """`update_stats()` averages real review ratings."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="test-avg-reviewer",
            password="TestPass123!",  # pragma: allowlist secret
        )
        cls.module = AppsModule.objects.create(
            module_name="avg-rating-test", category="other"
        )

    def test_avg_of_two_real_reviews_4_and_2_is_3_point_0(self):
        # Arrange
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
        # Act
        self.module.update_stats()
        # Assert
        assert self.module.avg_rating == Decimal("3.0")


# EOF
