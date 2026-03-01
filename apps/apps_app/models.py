#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Apps models — catalog, installations, stars, and reviews for workspace modules.

Every module (built-in or external) gets an AppsModule entry.
Users manage their workspace via ModuleInstallation records.
"""

from __future__ import annotations

from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

CATEGORY_CHOICES = [
    ("writing", "Writing"),
    ("visualization", "Visualization"),
    ("data", "Data"),
    ("analysis", "Analysis"),
    ("reference", "Reference"),
    ("utility", "Utility"),
    ("other", "Other"),
]

STATUS_CHOICES = [
    ("stable", "Stable"),
    ("wip", "WIP"),
    ("beta", "Beta"),
    ("deprecated", "Deprecated"),
]

VISIBILITY_CHOICES = [
    ("private", "Private"),
    ("unlisted", "Unlisted"),
    ("public", "Public"),
]


class AppsModule(models.Model):
    """Catalog entry for a workspace module."""

    # Links to registry (ModuleConfig.name)
    module_name = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text="Matches ModuleConfig.name in registry.py",
    )

    # Catalog metadata
    author = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="authored_modules",
    )
    short_description = models.CharField(max_length=200, blank=True)
    long_description = models.TextField(blank=True)
    category = models.CharField(
        max_length=30, choices=CATEGORY_CHOICES, default="other"
    )
    tags = models.JSONField(default=list, blank=True)
    homepage_url = models.URLField(blank=True)
    repository_url = models.URLField(blank=True)

    # Stats (denormalized for query performance)
    install_count = models.PositiveIntegerField(default=0)
    star_count = models.PositiveIntegerField(default=0)
    avg_rating = models.DecimalField(max_digits=2, decimal_places=1, default=0)

    # Status flags
    is_builtin = models.BooleanField(
        default=False,
        help_text="Built-in modules cannot be fully uninstalled, only disabled.",
    )
    is_featured = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default="stable",
        help_text="Development status: stable, wip, beta, deprecated.",
    )
    visibility = models.CharField(
        max_length=10,
        choices=VISIBILITY_CHOICES,
        default="private",
    )

    # Source project link (for user-submitted apps)
    project = models.OneToOneField(
        "project_app.Project",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="marketplace_module",
        help_text="Source project (for user-submitted apps)",
    )

    # Pinned commit (set on approval)
    pinned_commit = models.CharField(
        max_length=40,
        blank=True,
        help_text="SHA of the approved commit (set on approval)",
    )
    pinned_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "marketplace_app_marketplacemodule"
        ordering = ["-star_count", "-install_count"]
        verbose_name = "App"

    def __str__(self):
        return f"{self.module_name} ({self.category})"

    def update_stats(self):
        """Recompute denormalized stats from related objects."""
        self.star_count = self.stars_rel.count()
        self.install_count = self.installations.filter(is_enabled=True).count()
        reviews = self.reviews.all()
        if reviews.exists():
            self.avg_rating = round(
                reviews.aggregate(avg=models.Avg("rating"))["avg"], 1
            )
        else:
            self.avg_rating = 0
        self.save(update_fields=["star_count", "install_count", "avg_rating"])


class ModuleVersion(models.Model):
    """Version history for an app module."""

    module = models.ForeignKey(
        AppsModule, on_delete=models.CASCADE, related_name="versions"
    )
    version = models.CharField(max_length=20)
    changelog = models.TextField(blank=True)
    min_scitex_version = models.CharField(max_length=20, blank=True)
    is_stable = models.BooleanField(default=True)
    released_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "marketplace_app_moduleversion"
        unique_together = ("module", "version")
        ordering = ["-released_at"]
        verbose_name = "App Version"

    def __str__(self):
        return f"{self.module.module_name} v{self.version}"


class ModuleInstallation(models.Model):
    """Per-user installation state for a module."""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="installed_modules"
    )
    module = models.ForeignKey(
        AppsModule, on_delete=models.CASCADE, related_name="installations"
    )
    is_enabled = models.BooleanField(default=True)
    tab_order = models.IntegerField(default=50)
    installed_at = models.DateTimeField(auto_now_add=True)
    config = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "marketplace_app_moduleinstallation"
        unique_together = ("user", "module")
        ordering = ["tab_order"]
        verbose_name = "App Installation"

    def __str__(self):
        status = "enabled" if self.is_enabled else "disabled"
        return f"{self.user.username} → {self.module.module_name} ({status})"


class ModuleStar(models.Model):
    """User starring a module (bookmark / appreciation)."""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="starred_modules"
    )
    module = models.ForeignKey(
        AppsModule, on_delete=models.CASCADE, related_name="stars_rel"
    )
    starred_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "marketplace_app_modulestar"
        unique_together = ("user", "module")
        ordering = ["-starred_at"]

    def __str__(self):
        return f"{self.user.username} starred {self.module.module_name}"


class ModuleSubmission(models.Model):
    """Tracks module publication requests (private → public via admin review)."""

    STATUS_CHOICES = [
        ("pending", "Pending Review"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("changes_requested", "Changes Requested"),
    ]

    module = models.ForeignKey(
        AppsModule, on_delete=models.CASCADE, related_name="submissions"
    )
    submitted_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="module_submissions"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    reviewer = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_submissions",
    )
    review_note = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "marketplace_app_modulesubmission"
        ordering = ["-submitted_at"]
        verbose_name = "App Submission"

    def __str__(self):
        return f"{self.module.module_name} — {self.get_status_display()}"


class ModuleReview(models.Model):
    """User review and rating for a module."""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="module_reviews"
    )
    module = models.ForeignKey(
        AppsModule, on_delete=models.CASCADE, related_name="reviews"
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    title = models.CharField(max_length=100)
    body = models.TextField(blank=True)
    is_from_installer = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "marketplace_app_modulereview"
        unique_together = ("user", "module")
        ordering = ["-created_at"]
        verbose_name = "App Review"

    def __str__(self):
        return (
            f"{self.user.username} reviewed {self.module.module_name} ({self.rating}/5)"
        )


# EOF
