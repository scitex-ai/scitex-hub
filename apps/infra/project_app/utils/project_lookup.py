"""
Project lookup utilities for supporting both user and organization ownership.

Provides helper functions to resolve projects from URLs like:
- /<username>/<slug>/ - User-owned projects
- /<org-slug>/<slug>/ - Organization-owned projects
"""

from django.contrib.auth.models import User
from django.http import Http404

from apps.infra.organizations_app.models import Organization
from apps.infra.project_app.models import Project


def get_project_by_owner_slug(owner_identifier: str, slug: str) -> Project:
    """
    Get a project by owner identifier (username or org slug) and project slug.

    Tries to find:
    1. A project owned by a user with username=owner_identifier
    2. A project associated with an organization with slug=owner_identifier

    Args:
        owner_identifier: Username or organization slug
        slug: Project slug

    Returns:
        Project instance

    Raises:
        Http404: If project not found
    """
    # First, try to find by user ownership
    try:
        user = User.objects.get(username=owner_identifier)
        try:
            return Project.objects.get(owner=user, slug=slug)
        except Project.DoesNotExist:
            pass
    except User.DoesNotExist:
        pass

    # Second, try to find by organization ownership
    try:
        org = Organization.objects.get(slug=owner_identifier)
        try:
            return Project.objects.get(organization=org, slug=slug)
        except Project.DoesNotExist:
            pass
    except Organization.DoesNotExist:
        pass

    raise Http404(f"Project '{owner_identifier}/{slug}' not found")


def get_owner_context(owner_identifier: str) -> dict:
    """
    Get context about the owner (user or organization).

    Returns:
        dict with keys:
            - owner_type: 'user' or 'organization'
            - owner: User or Organization instance
            - username: The identifier for URLs
    """
    # Try user first
    try:
        user = User.objects.get(username=owner_identifier)
        return {
            "owner_type": "user",
            "owner": user,
            "username": user.username,
        }
    except User.DoesNotExist:
        pass

    # Try organization
    try:
        org = Organization.objects.get(slug=owner_identifier)
        return {
            "owner_type": "organization",
            "owner": org,
            "username": org.slug,  # Use slug as "username" for URL consistency
        }
    except Organization.DoesNotExist:
        pass

    raise Http404(f"Owner '{owner_identifier}' not found")
