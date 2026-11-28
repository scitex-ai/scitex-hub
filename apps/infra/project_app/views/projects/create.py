#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Project Create Views

Handle project creation with various initialization options.

A local creation is all-or-nothing: if any step fails, the row, its Gitea
repository and its working tree are removed, and the form comes back holding
the user's input and the reason (hub#1273, hub#1274).
"""

from __future__ import annotations

import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from ...models import Project, RemoteCredential
from ...services.project_creation import (
    discard_failed_creation,
    find_leftover,
    move_leftover_aside,
    user_project_path,
)
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
    LOCAL_CREATION_TABS,
    SCAFFOLD_TEMPLATES,
    generate_unique_slug,
    get_template_map,
    validate_project_name,
    verify_gitea_availability,
)
from .create_remote import create_remote_project

logger = logging.getLogger(__name__)

OFFERED_TEMPLATES = frozenset(
    template for init, template in LOCAL_CREATION_TABS.values() if init == "template"
)


def _tab_for(init_type, template_type):
    """The /new/ tab a POST came from, so a re-rendered form reopens it."""
    for tab, fields in LOCAL_CREATION_TABS.items():
        if fields == (init_type, template_type if init_type == "template" else ""):
            return tab
    return {"github": "import", "git": "import"}.get(init_type, "minimal")


def _render_form(request, values):
    """The /new/ page again, holding what the user typed."""
    context = {
        "template_map": get_template_map(),
        "remote_credentials": RemoteCredential.objects.filter(
            user=request.user, is_active=True
        ).order_by("name"),
        **values,
    }
    return render(request, "project_app/projects/create.html", context)


def _create_local_project(request, manager, fields):
    """Save the row and run the chosen initialisation; True when it all worked.

    Records the reason with ``messages`` on failure. An unexpected exception
    is a failure like any other: it must reach the rollback, not a 500 that
    leaves a half-made project behind.
    """
    init_type = fields["init_type"]
    template_type = fields["template_type"]
    project = Project(
        name=fields["name"],
        slug=fields["slug"],
        description=fields["description"],
        owner=request.user,
        # Set at create time: the post_save Gitea signal reads it.
        visibility=fields["visibility"],
    )
    # Gitea creates and clones the repository; for a scaffold template its
    # generic Writer seed must leave that clone to the template step.
    project._template_scaffold_pending = (
        init_type == "template" and template_type in SCAFFOLD_TEMPLATES
    )
    try:
        project.save()
        if init_type == "gitea":
            ok = handle_gitea_creation(request, project)
        elif init_type == "github":
            ok = handle_github_import(request, project, manager, fields["git_url"])
        elif init_type == "template" and template_type == "app":
            ok = handle_app_template_creation(request, project, manager)
        elif init_type == "template":
            ok = handle_template_creation(request, project, manager, template_type)
        elif init_type == "git":
            ok = handle_git_clone(request, project, manager, fields["git_url"])
        else:
            ok = handle_empty_creation(request, project, manager)
    except Exception as exc:
        logger.exception("Creating project %s/%s failed", request.user, project.slug)
        messages.error(request, f"Project creation failed: {exc}")
        ok = False
    return project, ok


@login_required
def project_create(request):
    """Create new project — unified tabbed page."""
    if request.method == "POST":
        # The max_projects quota (config/settings/quotas.py + UserQuota) and
        # spend controls: a new project is a storage write, refused when the
        # account's storage is read-only (cap reached or restricted).
        from apps.infra.spend_app.decorators import refusal_response
        from apps.infra.spend_app.services import gate

        try:
            gate.check_project_quota(request.user)
            gate.require(request.user, gate.Action.WRITE_STORAGE)
        except gate.Refused as exc:
            return refusal_response(request, exc)

        name = request.POST.get("name", "").strip()
        description = request.POST.get("description", "").strip()
        init_type = request.POST.get("init_type", "empty")
        template_type = request.POST.get("template_type", "research")
        git_url = request.POST.get("git_url", "").strip()
        init_scitex = request.POST.get("init_scitex") == "true"
        visibility = (
            "public" if request.POST.get("visibility") == "public" else "private"
        )

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
        from apps.infra.project_app.services.project_filesystem import (
            get_project_filesystem_manager,
        )

        manager = get_project_filesystem_manager(request.user)

        # If importing from Git and no name provided, extract from URL
        if not name and git_url and init_type in ["github", "git"]:
            name = Project.extract_repo_name_from_url(git_url)

        form_values = {
            "active_tab": _tab_for(init_type, template_type),
            "name": name,
            "description": description,
            "init_type": init_type,
            "visibility": visibility,
            "git_url": git_url,
        }

        # Validate project name
        is_valid, error_msg = validate_project_name(request, name)
        if not is_valid:
            messages.error(request, error_msg)
            return _render_form(request, form_values)

        if init_type == "template" and template_type not in OFFERED_TEMPLATES:
            messages.error(request, f'Unknown project template "{template_type}".')
            return _render_form(request, form_values)

        # Generate slug and verify Gitea availability
        unique_slug = generate_unique_slug(name, request.user)
        is_available, gitea_msg = verify_gitea_availability(
            request, request.user, unique_slug
        )
        if not is_available:
            messages.error(request, gitea_msg)
            return _render_form(request, form_values)
        elif gitea_msg:  # Warning case
            messages.warning(request, gitea_msg)

        # A folder no project owns would pass for this project's clone.
        leftover = find_leftover(request.user, unique_slug)
        if leftover is not None:
            try:
                move_leftover_aside(request.user, leftover)
            except OSError:
                logger.exception("Could not move leftover folder %s", leftover)
                messages.error(
                    request,
                    f'Files from an earlier attempt named "{name}" are in the '
                    "way and could not be cleared. Please choose another name "
                    "or contact support.",
                )
                return _render_form(request, form_values)

        project, ok = _create_local_project(
            request,
            manager,
            {
                "name": name,
                "slug": unique_slug,
                "description": description,
                "visibility": visibility,
                "init_type": init_type,
                "template_type": template_type,
                "git_url": git_url,
            },
        )
        if not ok:
            discard_failed_creation(
                project, user_project_path(request.user, unique_slug)
            )
            messages.error(
                request,
                "Nothing was kept, so you can try again with the same name. "
                "Your entries are below.",
            )
            return _render_form(request, form_values)

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
