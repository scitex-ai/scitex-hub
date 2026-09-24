#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Project Utilities Service

Centralized utilities for project management across all apps (Writer, Scholar, etc.)
This prevents code duplication and ensures consistent project selection logic.
"""

import logging
from urllib.parse import urlparse

from apps.infra.project_app.models import Project

logger = logging.getLogger(__name__)

# Project scope: "single" (one current project) or "all" (the user's whole
# scope — the "All projects" selector option). Stored in the session only:
# it is a view preference, not identity, so it must never touch
# last_active_repository or the current_project_* session keys that
# get_current_project() reads.
PROJECT_SCOPE_SINGLE = "single"
PROJECT_SCOPE_ALL = "all"
_PROJECT_SCOPES = (PROJECT_SCOPE_SINGLE, PROJECT_SCOPE_ALL)


def set_project_scope(request, scope):
    """Persist the user's project scope choice ("single" or "all")."""
    if scope not in _PROJECT_SCOPES:
        raise ValueError(
            f"unknown project scope {scope!r}; expected one of {_PROJECT_SCOPES}."
        )
    request.session["project_scope"] = scope


def get_project_scope(request):
    """The user's project scope; "single" unless they picked "All projects"."""
    scope = request.session.get("project_scope", PROJECT_SCOPE_SINGLE)
    return scope if scope in _PROJECT_SCOPES else PROJECT_SCOPE_SINGLE


def is_all_projects_scope(request):
    """True when the user picked the "All projects" selector option."""
    return get_project_scope(request) == PROJECT_SCOPE_ALL


def _owned_project(user, slug):
    if not slug:
        return None
    return Project.objects.select_related("owner").filter(owner=user, slug=slug).first()


def get_requested_project(request, user=None):
    """The project this request names explicitly, or None.

    ``?project=<slug>`` (or ``<owner>/<slug>``) wins, then a same-site Referer
    under ``/<username>/<slug>/``. Owned and explicitly shared projects match;
    unrelated public/private projects do not.
    """
    user = user or request.user
    if not getattr(user, "is_authenticated", False):
        return None

    requested = (request.GET.get("project") or "").strip().strip("/")
    if requested:
        from .project_scope import find_accessible_project

        project = find_accessible_project(user, requested)
        if project:
            return project

    referer = urlparse(request.META.get("HTTP_REFERER", ""))
    if referer.netloc and referer.netloc != request.get_host():
        return None
    parts = [p for p in referer.path.split("/") if p]
    if len(parts) >= 2:
        from .project_scope import find_accessible_project

        return find_accessible_project(user, f"{parts[0]}/{parts[1]}")
    return None


def remember_current_project(request, project):
    """Persist a project choice to BOTH stores so every reader agrees."""
    from .project_scope import project_key

    request.session["current_project_key"] = project_key(project)
    request.session["current_project_slug"] = project.slug
    profile = getattr(request.user, "profile", None)
    if profile is not None and profile.last_active_repository_id != project.id:
        profile.last_active_repository = project
        profile.save(update_fields=["last_active_repository"])


def get_current_project(request, user=None):
    """
    Get the current project for a user, with fallback logic.

    Logic priority:
    1. User's last_active_repository (if authenticated) — what the header
       project selector writes, so an explicit choice wins.
    2. Session-based project selection (current_project_slug)
    3. First project owned by the user

    There used to be a higher-priority step reading a ``current_project_id``
    session key, documented as "from shareable links". Nothing in the codebase
    ever wrote that key, so the branch was unreachable and the feature it
    advertised did not exist. It is removed rather than left as a promise the
    code does not keep; if shareable links are built later, they should set
    ``current_project_slug`` through ``set_current_project`` like every other
    writer, so there stays exactly one session key for "current project".

    Args:
        request: Django request object
        user: Optional User object. If None, uses request.user

    Returns:
        Project: The current project for the user
    """
    # Determine user
    if user is None:
        if request.user.is_authenticated:
            user = request.user
        else:
            # Return None for visitor users - let caller handle guest creation
            return None

    current_project = None
    is_authenticated = (
        user.is_authenticated
        if hasattr(user, "is_authenticated")
        else (user.username and not user.username.startswith("guest-"))
    )

    # HIGHEST PRIORITY: the header selector's last visited accessible project.
    if is_authenticated:
        from .project_scope import last_visited_project

        lar = last_visited_project(user)
        if lar is not None:
            logger.info(
                f"Using last_active_repository for user {user.username}: {lar.name}"
            )
            return lar

    # New session format includes the owner, so shared projects with the same
    # slug as an owned project remain unambiguous.
    current_project_key = request.session.get("current_project_key")
    if current_project_key:
        from .project_scope import find_accessible_project

        current_project = find_accessible_project(user, current_project_key)
        if current_project is not None:
            return current_project
        request.session.pop("current_project_key", None)

    # Fallback: try session-based project selection by slug
    current_project_slug = request.session.get("current_project_slug")
    if current_project_slug:
        try:
            current_project = Project.objects.select_related("owner").get(
                slug=current_project_slug, owner=user
            )
            logger.info(
                f"Using session project for user {user.username}: {current_project.name}"
            )
            return current_project
        except Project.DoesNotExist:
            logger.warning(f"Session project not found: {current_project_slug}")
            # Clear invalid session
            request.session.pop("current_project_slug", None)

    # Final fallback: get first project or None
    try:
        current_project = (
            Project.objects.filter(owner=user).select_related("owner").first()
        )
        if current_project:
            logger.info(
                f"Using first user project for {user.username}: {current_project.name}"
            )
            # NOT a choice, so it is NOT remembered. This branch used to call
            # remember_current_project(), which writes BOTH the session keys and
            # profile.last_active_repository — so merely rendering a page made a
            # user who had never chosen anything look like a user who had, and
            # the first-login welcome could never show (the launcher built its
            # context by calling this, the pointer got written, and
            # profile_has_explicit_choice() then read True). An implicit default
            # may be DISPLAYED; only a real choice may be PERSISTED. Card
            # hub-first-login-project-workspace-onboarding-20260917.
            return current_project
    except Exception as e:
        logger.error(f"Error retrieving project for user {user.username}: {e}")

    return None


def set_current_project(request, project):
    """
    Set the current project in session for a user.

    Args:
        request: Django request object
        project: Project to set as current
    """
    if project:
        remember_current_project(request, project)
        logger.info(f"Set current project in session: {project.slug}")


def get_or_create_default_project(user, is_guest=False):
    """
    Get or create a default project for a user (including guests).

    Note: Writer directory is NOT created here - it's created on-demand
    when the user actually uses the writer feature.

    Args:
        user: User to get/create project for
        is_guest: Whether this is a guest user

    Returns:
        Project: The user's default project
    """
    # Check if user already has projects
    existing_project = Project.objects.filter(owner=user).first()
    if existing_project:
        logger.info(f"Using existing project: {existing_project.name}")
        return existing_project

    # Create default project (without writer directory - created on-demand)
    if is_guest:
        project_name = "Guest Demo Project"
        description = (
            "Temporary demo project for guest user. Sign up to keep your work!"
        )
    else:
        project_name = f"{user.username}'s Project"
        description = f"Default project for {user.username}"

    # Generate unique slug (per-owner uniqueness)
    slug = Project.generate_unique_slug(project_name, owner=user)

    # Create the project (data_location will be set when writer dir is created)
    project = Project.objects.create(
        name=project_name,
        slug=slug,
        description=description,
        owner=user,
        visibility="private",
    )

    logger.info(f"Created default project: {project.name} (slug: {slug})")
    return project


# EOF
