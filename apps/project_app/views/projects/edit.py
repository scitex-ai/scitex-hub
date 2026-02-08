#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Project Edit View

Handle project editing.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages

from ...models import Project


@login_required
def project_edit(request, username, slug):
    """Edit project"""
    user = get_object_or_404(User, username=username)
    project = get_object_or_404(Project, slug=slug, owner=user)

    # Only project owner can edit
    if project.owner != request.user:
        messages.error(request, "You don't have permission to edit this project.")
        return redirect("project_app:detail", username=username, slug=slug)

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        description = request.POST.get("description", "").strip()

        if name:
            project.name = name
        if description:
            project.description = description

        project.save()
        messages.success(request, "Project updated successfully")
        return redirect("project_app:detail", username=username, slug=project.slug)

    context = {"project": project}
    return render(request, "project_app/projects/edit.html", context)


# EOF
