#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Project Delete View

Handle project deletion.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages

from ...models import Project


@login_required
def project_delete(request, username, slug):
    """Delete project"""
    user = get_object_or_404(User, username=username)
    project = get_object_or_404(Project, slug=slug, owner=user)

    # Only project owner can delete
    if project.owner != request.user:
        messages.error(request, "You don't have permission to delete this project.")
        return redirect("project_app:detail", username=username, slug=slug)

    if request.method == "POST":
        # Verify confirmation text matches "username/slug"
        confirmation = request.POST.get("confirmation", "").strip()
        expected_confirmation = f"{username}/{slug}"

        if confirmation != expected_confirmation:
            messages.error(
                request,
                f'Confirmation text does not match. Please type "{expected_confirmation}" exactly.',
            )
            return render(
                request,
                "project_app/delete.html",
                {"project": project},
            )

        project_name = project.name
        project.delete()
        messages.success(request, f'Project "{project_name}" deleted successfully')
        return redirect("project_app:list", username=request.user.username)

    context = {"project": project}
    return render(request, "project_app/projects/delete.html", context)


# EOF
