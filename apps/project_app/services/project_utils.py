#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Project Utilities Service

Centralized utilities for project management across all apps (Writer, Scholar, etc.)
This prevents code duplication and ensures consistent project selection logic.
"""

from apps.project_app.models import Project
import logging

logger = logging.getLogger(__name__)


def get_current_project(request, user=None):
    """
    Get the current project for a user, with fallback logic.

    Logic priority:
    1. Direct project ID from session (from shareable links)
    2. User's last_active_repository (if authenticated)
    3. Session-based project selection (current_project_slug)
    4. Default project (created if needed)

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

    # HIGHEST PRIORITY: Direct project ID from session (set by shareable links)
    current_project_id = request.session.get("current_project_id")
    if current_project_id:
        try:
            current_project = Project.objects.get(id=current_project_id)
            # Verify user has permission to view
            if current_project.can_view(user):
                logger.info(
                    f"Using direct project ID from session for user {user.username}: {current_project.name}"
                )
                return current_project
            else:
                # Clear invalid session
                request.session.pop("current_project_id", None)
                logger.warning(
                    f"User {user.username} doesn't have permission for project {current_project_id}"
                )
        except Project.DoesNotExist:
            logger.warning(f"Session project ID not found: {current_project_id}")
            # Clear invalid session
            request.session.pop("current_project_id", None)

    # For authenticated users, try header selector
    if is_authenticated:
        if hasattr(user, "profile") and user.profile.last_active_repository:
            current_project = user.profile.last_active_repository
            logger.info(
                f"Using last_active_repository for user {user.username}: {current_project.name}"
            )
            return current_project

    # Fallback: try session-based project selection by slug
    current_project_slug = request.session.get("current_project_slug")
    if current_project_slug:
        try:
            current_project = Project.objects.get(slug=current_project_slug, owner=user)
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
        current_project = Project.objects.filter(owner=user).first()
        if current_project:
            logger.info(
                f"Using first user project for {user.username}: {current_project.name}"
            )
            # Store in session for future requests
            request.session["current_project_slug"] = current_project.slug
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
        request.session["current_project_slug"] = project.slug
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
