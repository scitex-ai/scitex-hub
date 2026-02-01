#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-04 (ywatanabe)"
# File: /home/ywatanabe/proj/scitex-cloud/apps/project_app/views/integration_views.py
# ----------------------------------------
"""
GitHub and Repository Integration Views

This module handles views related to:
- GitHub integration for projects
- Repository maintenance and health checks
- Repository synchronization with Gitea
"""

from __future__ import annotations
import os

__FILE__ = "./apps/project_app/views/integration_views.py"
__DIR__ = os.path.dirname(__FILE__)
# ----------------------------------------

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User

from ..models import Project


@login_required
def repository_maintenance(request, username):
    """
    Repository health check and maintenance dashboard.

    Shows the health status of all repositories for a user and allows them to:
    - View repository synchronization status
    - Delete orphaned Gitea repositories
    - Re-sync repositories with Gitea
    """
    # Only allow users to view their own maintenance dashboard
    user = get_object_or_404(User, username=username)
    if user != request.user and not request.user.is_staff:
        messages.error(request, "You don't have permission to view this page.")
        return redirect("user_projects:list", username=request.user.username)

    context = {
        "username": username,
        "user": user,
        "page_title": "Repository Maintenance",
        "active_tab": "repositories",
    }
    return render(
        request, "project_app/repository/admin_repository_maintenance.html", context
    )


@login_required
def github_integration(request, username, slug):
    """GitHub integration for project"""
    user = get_object_or_404(User, username=username)
    project = get_object_or_404(Project, slug=slug, owner=user)

    # Only project owner can manage GitHub integration
    if project.owner != request.user:
        messages.error(
            request,
            "You don't have permission to manage GitHub integration for this project.",
        )
        return redirect("user_projects:detail", username=username, slug=slug)

    context = {
        "project": project,
    }
    return render(request, "project_app/github_integration.html", context)
