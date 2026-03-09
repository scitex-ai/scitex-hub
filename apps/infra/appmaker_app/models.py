#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
App Maker models — user-authored workspace apps and their execution history.

UserModule stores the source code and metadata for a custom app.
ModuleExecution tracks each run with timing, memory, status, and outputs.
"""

from __future__ import annotations

from django.contrib.auth.models import User
from django.db import models

from apps.workspace.apps_app.models import CATEGORY_CHOICES
from apps.infra.project_app.models import Project

VISIBILITY_CHOICES = [
    ("private", "Private"),
    ("group", "Group"),
    ("public", "Public"),
]

EXECUTION_STATUS_CHOICES = [
    ("running", "Running"),
    ("success", "Success"),
    ("error", "Error"),
    ("timeout", "Timeout"),
]


class UserModule(models.Model):
    """A user-authored workspace module with Python source code."""

    slug = models.SlugField(max_length=60, db_index=True)
    label = models.CharField(max_length=100)
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="user_modules",
    )
    source_code = models.TextField()
    icon = models.CharField(max_length=50, default="fa-puzzle-piece")
    category = models.CharField(
        max_length=30,
        choices=CATEGORY_CHOICES,
        default="utility",
    )
    description = models.CharField(max_length=300, blank=True)
    version = models.CharField(max_length=20, default="0.1.0")
    dependencies = models.JSONField(default=list)
    visibility = models.CharField(
        max_length=10,
        choices=VISIBILITY_CHOICES,
        default="private",
    )
    shared_with_project = models.ForeignKey(
        Project,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="shared_user_modules",
    )
    # Git source tracking (for modules imported from GitHub/git repos)
    source_repo_url = models.URLField(max_length=500, blank=True, default="")
    source_repo_ref = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Branch, tag, or commit hash",
    )

    is_active = models.BooleanField(default=True)
    run_count = models.PositiveIntegerField(default=0)
    last_run_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "modulemaker_app_usermodule"
        unique_together = ("author", "slug")
        ordering = ["-updated_at"]
        verbose_name = "User App"

    @property
    def is_git_sourced(self):
        return bool(self.source_repo_url)

    def __str__(self):
        return f"{self.author.username}/{self.slug} v{self.version}"


class ModuleExecution(models.Model):
    """Record of a single module execution with timing and output data."""

    module = models.ForeignKey(
        UserModule,
        on_delete=models.CASCADE,
        related_name="executions",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="module_executions",
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="module_executions",
    )
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    wall_time_ms = models.PositiveIntegerField(default=0)
    peak_memory_mb = models.PositiveIntegerField(default=0)
    status = models.CharField(
        max_length=10,
        choices=EXECUTION_STATUS_CHOICES,
        default="running",
    )
    error_message = models.TextField(blank=True)
    output_json = models.JSONField(default=list)

    class Meta:
        db_table = "modulemaker_app_moduleexecution"
        ordering = ["-started_at"]
        verbose_name = "App Execution"

    def __str__(self):
        return f"{self.module.slug} run by {self.user.username} ({self.status})"


# EOF
