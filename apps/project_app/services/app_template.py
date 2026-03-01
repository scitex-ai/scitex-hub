#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""App template scaffolding — delegates to scitex_cloud.app_tools."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def create_app_from_template(project, app_name=None):
    """Scaffold required app files in a project directory.

    Delegates to scitex_cloud.app_tools.scaffold() for the actual file generation.
    Returns list of created file paths, or raises on failure.
    """
    from scitex_cloud.app_tools import scaffold

    project_dir = _get_project_dir(project)
    name = app_name or project.slug.replace("-", "_")

    if not name.endswith("_app"):
        name = f"{name}_app"

    created = scaffold(
        target_dir=str(project_dir),
        name=name,
    )

    logger.info(
        "[app_template] Scaffolded %d files for %s/%s",
        len(created),
        project.owner.username,
        project.slug,
    )
    return created


def _get_project_dir(project):
    """Resolve local project directory path."""
    from pathlib import Path

    from django.conf import settings

    return (
        Path(settings.BASE_DIR)
        / "data"
        / "users"
        / project.owner.username
        / "proj"
        / project.slug
    )


# EOF
