#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Project Create from Template View

Create template structure for an existing empty project.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages

from ...models import Project


@login_required
def project_create_from_template(request, username, slug):
    """Create template structure for an existing empty project"""
    user = get_object_or_404(User, username=username)
    project = get_object_or_404(Project, slug=slug, owner=user)

    # Only project owner can create template
    if project.owner != request.user:
        messages.error(request, "Only project owner can create template structure.")
        return redirect("user_projects:detail", username=username, slug=slug)

    if request.method == "POST":
        # Create template structure
        from apps.project_app.services.project_filesystem import (
            get_project_filesystem_manager,
        )

        manager = get_project_filesystem_manager(project.owner)

        try:
            success, path = manager.create_project_from_template(project)

            if success:
                messages.success(
                    request,
                    f'Template structure created successfully for "{project.name}"!',
                )
            else:
                messages.error(request, "Failed to create template structure.")
        except Exception as e:
            messages.error(request, f"Failed to create template structure: {str(e)}")

        return redirect("user_projects:detail", username=username, slug=slug)

    # GET request - show confirmation page or redirect
    return redirect("user_projects:detail", username=username, slug=slug)


# EOF
