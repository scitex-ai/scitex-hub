#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Project Create Views

Handle project creation with various initialization options.
"""

from __future__ import annotations

import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils.safestring import mark_safe

from ...models import Project, RemoteCredential
from .create_handlers import (
    handle_app_template_creation,
    handle_empty_creation,
    handle_git_clone,
    handle_gitea_creation,
    handle_github_import,
    handle_scitex_initialization,
    handle_template_creation,
)
from .create_helpers import (
    generate_unique_slug,
    get_template_map,
    validate_project_name,
    verify_gitea_availability,
)
from .create_remote import create_remote_project

logger = logging.getLogger(__name__)


@login_required
def project_create(request):
    """Create new project — unified tabbed page."""
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        description = request.POST.get("description", "").strip()
        init_type = request.POST.get("init_type", "empty")
        template_type = request.POST.get("template_type", "research")
        git_url = request.POST.get("git_url", "").strip()
        init_scitex = request.POST.get("init_scitex") == "true"

        # Project type (local or remote)
        project_type = request.POST.get("project_type", "local")

        # Remote project fields
        remote_credential_id = request.POST.get("remote_credential_id")
        remote_path = request.POST.get("remote_path", "").strip()

        # Handle remote project creation separately
        if project_type == "remote":
            return create_remote_project(
                request, name, description, remote_credential_id, remote_path
            )

        # Handle TRIP project creation separately
        if project_type == "trip":
            from .create_trip import create_trip_project

            return create_trip_project(
                request, name, description, remote_credential_id, remote_path
            )

        # Initialize directory manager for all init types (local projects only)
        from apps.project_app.services.project_filesystem import (
            get_project_filesystem_manager,
        )

        manager = get_project_filesystem_manager(request.user)

        # If importing from Git and no name provided, extract from URL
        if not name and git_url and init_type in ["github", "git"]:
            name = Project.extract_repo_name_from_url(git_url)

        # Map init_type + template_type to active tab for error re-display
        if project_type == "remote":
            active_tab = "remote"
        elif init_type == "template":
            _tpl_tab = {"minimal": "minimal", "research": "full", "app": "app"}
            active_tab = _tpl_tab.get(template_type, "minimal")
        else:
            _tab_map = {"github": "import", "git": "import", "gitea": "blank"}
            active_tab = _tab_map.get(init_type, "minimal")

        # Validate project name
        is_valid, error_msg = validate_project_name(request, name)
        if not is_valid:
            messages.error(request, error_msg)
            remote_credentials = RemoteCredential.objects.filter(
                user=request.user, is_active=True
            ).order_by("name")
            context = {
                "template_map": get_template_map(),
                "remote_credentials": remote_credentials,
                "active_tab": active_tab,
                "name": name,
                "description": description,
                "init_type": init_type,
                "git_url": git_url,
            }
            return render(request, "project_app/projects/create.html", context)

        # Generate slug and verify Gitea availability
        unique_slug = generate_unique_slug(name, request.user)
        is_available, gitea_msg = verify_gitea_availability(
            request, request.user, unique_slug
        )
        if not is_available:
            messages.error(request, mark_safe(gitea_msg))
            remote_credentials = RemoteCredential.objects.filter(
                user=request.user, is_active=True
            ).order_by("name")
            context = {
                "template_map": get_template_map(),
                "remote_credentials": remote_credentials,
                "active_tab": active_tab,
                "name": name,
                "description": description,
                "init_type": init_type,
            }
            return render(request, "project_app/projects/create.html", context)
        elif gitea_msg:  # Warning case
            messages.warning(request, gitea_msg)

        try:
            project = Project.objects.create(
                name=name,
                slug=unique_slug,
                description=description,
                owner=request.user,
            )
        except Exception as e:
            logger.error(f"Failed to create project: {e}")
            messages.error(request, f"Failed to create project: {str(e)}")
            return redirect(f"/{request.user.username}/")

        # Handle different initialization types
        success = True
        if init_type == "gitea":
            success = handle_gitea_creation(request, project)
        elif init_type == "github":
            success = handle_github_import(request, project, manager, git_url)
        elif init_type == "template" and template_type == "app":
            success = handle_app_template_creation(request, project, manager)
        elif init_type == "template":
            success = handle_template_creation(request, project, manager, template_type)
        elif init_type == "git":
            success = handle_git_clone(request, project, manager, git_url)
        else:
            # Create empty project
            success = handle_empty_creation(request, project, manager)

        if not success:
            return redirect(f"/{request.user.username}/")

        # Initialize SciTeX Writer template if requested
        if init_scitex:
            handle_scitex_initialization(request, project, manager)

        return redirect(f"/{request.user.username}/{project.slug}/")

    # GET request - unified tabbed page (type= param selects initial tab via JS)
    template_map = get_template_map()
    remote_credentials = RemoteCredential.objects.filter(
        user=request.user, is_active=True
    ).order_by("name")

    context = {
        "template_map": template_map,
        "remote_credentials": remote_credentials,
    }

    return render(request, "project_app/projects/create.html", context)


# EOF
