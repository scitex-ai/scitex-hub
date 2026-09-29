#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Guided-sample provisioning — the explicit third choice on first login.

SSOT: docs/product/PRIVATE_BETA_LOGIN_TO_WOW.md §3 and
apps/infra/accounts_app/onboarding.py. The sample exists ONLY after the user
clicks "Use a guided sample": this module is called from a POST view, never
from page load, signals, or read paths.

What the user gets: a private project named "Welcome tour" built from the
``minimal`` template plus the first-project seed payload (sample dataset,
FigRecipe recipe + PNG, references, writer abstract), then landed inside it
as their explicitly chosen project.
"""

from __future__ import annotations

import logging

from ..models import Project
from .project_filesystem import get_project_filesystem_manager

logger = logging.getLogger(__name__)

SAMPLE_PROJECT_NAME = "Welcome tour"
SAMPLE_PROJECT_DESCRIPTION = (
    "A guided sample: literature, data, a figure and a manuscript "
    "connected in one project. Delete it any time."
)


def create_guided_sample_project(user) -> Project:
    """Create, seed and return the guided-sample project for ``user``.

    Raises the underlying exception on failure after deleting the partial
    project row, so a retry starts clean. Callers own messaging/redirect.
    """
    from ..views.projects.create_helpers import generate_unique_slug

    if Project.objects.filter(name=SAMPLE_PROJECT_NAME, owner=user).exists():
        return Project.objects.get(name=SAMPLE_PROJECT_NAME, owner=user)

    manager = get_project_filesystem_manager(user)
    project = Project.objects.create(
        name=SAMPLE_PROJECT_NAME,
        slug=generate_unique_slug(SAMPLE_PROJECT_NAME, user),
        description=SAMPLE_PROJECT_DESCRIPTION,
        owner=user,
    )
    try:
        success, path = manager.create_project_directory(
            project, use_template=True, template_type="minimal"
        )
        if not success:
            raise RuntimeError("template directory creation failed")
        root = manager.get_project_root_path(project) or path
        from .first_project_samples import try_seed_first_project_samples

        try_seed_first_project_samples(root)
    except Exception:
        logger.exception("guided-sample provisioning failed for %s", user)
        project.delete()
        raise
    return project
