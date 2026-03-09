#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Project Creation Helper Functions

Utilities for project creation validation and initialization.
"""

import logging

from django.utils.text import slugify

from ...models import Project

logger = logging.getLogger(__name__)


def get_available_templates():
    """Get available project templates from scitex package (source of truth)."""
    try:
        from scitex.template import get_available_templates_info

        return get_available_templates_info()
    except ImportError:
        logger.warning("scitex.template not available, using empty template list")
        return []


def get_template_map():
    """Get templates as a dict keyed by id for direct lookup in templates."""
    templates = get_available_templates()
    return {t["id"]: t for t in templates}


def validate_project_name(request, name):
    """
    Validate project name.

    Returns:
        tuple: (is_valid, error_message)
    """
    if not name:
        return False, "Project name is required"

    is_valid, error_message = Project.validate_repository_name(name)
    if not is_valid:
        return False, error_message

    if Project.objects.filter(name=name, owner=request.user).exists():
        return (
            False,
            f'You already have a project named "{name}". Please choose a different name.',
        )

    return True, None


def verify_gitea_availability(request, user, unique_slug):
    """
    Verify that repository doesn't already exist in Gitea.

    Returns:
        tuple: (is_available, error_message)
    """
    try:
        from apps.infra.gitea_app.api_client import GiteaAPIError, GiteaClient

        client = GiteaClient()

        try:
            existing_repo = client.get_repository(owner=user.username, repo=unique_slug)
            if existing_repo:
                error_msg = (
                    f'Repository "{unique_slug}" already exists in Gitea. '
                    f"This is likely an orphaned repository from a previous project. "
                    f'Please visit your <a href="/{user.username}/settings/repositories/">repository maintenance page</a> to clean it up.'
                )
                return False, error_msg
        except GiteaAPIError:
            # Repository doesn't exist in Gitea - this is good
            pass

        return True, None

    except Exception as e:
        # Log warning but don't fail - Gitea might be temporarily unavailable
        logger.warning(f"Could not verify Gitea repository availability: {e}")
        return (
            True,
            "Could not verify repository name with Gitea. Proceeding with caution.",
        )


def generate_unique_slug(name, user):
    """Generate a unique slug from project name."""
    base_slug = slugify(name)
    return Project.generate_unique_slug(base_slug, owner=user)


# EOF
