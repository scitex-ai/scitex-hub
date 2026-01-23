#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Project Creation Helper Functions

Utilities for project creation validation and initialization.
"""

import logging

from django.contrib import messages
from django.utils.text import slugify
from django.utils.safestring import mark_safe

from ...models import Project

logger = logging.getLogger(__name__)


def get_available_templates():
    """Get available project templates from scitex or provide fallback."""
    try:
        from scitex.template import get_available_templates_info
        return get_available_templates_info()
    except ImportError:
        # Fallback if scitex not available
        return [
            {
                "id": "research",
                "name": "Research Project",
                "description": "Full scientific workflow structure",
            },
            {
                "id": "pip_project",
                "name": "Python Package",
                "description": "Pip-installable package template",
            },
            {
                "id": "singularity",
                "name": "Singularity Container",
                "description": "Container-based project",
            },
        ]


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
        return False, f'You already have a project named "{name}". Please choose a different name.'

    return True, None


def verify_gitea_availability(request, user, unique_slug):
    """
    Verify that repository doesn't already exist in Gitea.

    Returns:
        tuple: (is_available, error_message)
    """
    try:
        from apps.gitea_app.api_client import GiteaClient, GiteaAPIError

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
        return True, f"Could not verify repository name with Gitea. Proceeding with caution."


def generate_unique_slug(name, user):
    """Generate a unique slug from project name."""
    base_slug = slugify(name)
    return Project.generate_unique_slug(base_slug, owner=user)


# EOF
