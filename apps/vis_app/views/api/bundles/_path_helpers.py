"""
Path resolution helpers for bundle APIs.

Resolves relative paths to absolute paths using project context.
Django acts as a thin wrapper - these helpers just resolve paths
before passing to scitex package.
"""

import logging
from pathlib import Path
from typing import Optional, Union

logger = logging.getLogger(__name__)


def resolve_bundle_path(
    bundle_path: Union[str, Path],
    project_owner: Optional[str] = None,
    project_slug: Optional[str] = None,
    user: Optional["User"] = None,
) -> Path:
    """
    Resolve a relative bundle path to absolute using project context.

    Args:
        bundle_path: Path (relative or absolute) to bundle
        project_owner: Project owner username
        project_slug: Project slug
        user: Django User object (fallback for project resolution)

    Returns:
        Absolute Path to the bundle
    """
    path = Path(bundle_path)

    if path.is_absolute():
        return path

    # Try project-based resolution
    if project_owner and project_slug:
        try:
            from apps.project_app.models import Project

            project = Project.objects.get(
                owner__username=project_owner, slug=project_slug
            )
            resolved = project.get_local_path() / bundle_path
            logger.debug(f"[resolve_bundle_path] Resolved via project: {resolved}")
            return resolved
        except Exception as e:
            logger.warning(f"[resolve_bundle_path] Failed to resolve project: {e}")

    # Fallback: user's default project
    if user:
        try:
            from apps.project_app.services.project_utils import get_user_project

            project = get_user_project(user)
            if project:
                resolved = project.get_local_path() / bundle_path
                logger.debug(
                    f"[resolve_bundle_path] Resolved via user project: {resolved}"
                )
                return resolved
        except Exception as e:
            logger.warning(f"[resolve_bundle_path] Failed to get user project: {e}")

    # Return as-is if resolution fails
    logger.warning(
        f"[resolve_bundle_path] Could not resolve relative path: {bundle_path}"
    )
    return path
