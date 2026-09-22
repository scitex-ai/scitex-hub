#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""POST-only endpoint for the first-login "Use a guided sample" choice.

SSOT: docs/product/PRIVATE_BETA_LOGIN_TO_WOW.md §3 — the sample is created
only after the user's explicit click. GET is rejected (405) so crawlers and
prefetch can never trigger provisioning.
"""

from __future__ import annotations

import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.views.decorators.http import require_POST

from ...services.guided_sample import create_guided_sample_project
from ...services.project_utils import set_current_project

logger = logging.getLogger(__name__)


@login_required
@require_POST
def guided_sample_create(request):
    """Create the guided-sample project and land the user inside it."""
    try:
        project = create_guided_sample_project(request.user)
    except Exception:
        logger.exception("guided-sample creation failed")
        messages.error(
            request,
            "Could not prepare the guided sample. "
            "Please create a project instead — nothing was changed.",
        )
        return redirect("project_create")
    set_current_project(request, project)
    messages.success(
        request,
        "Welcome aboard — this sample project is yours to explore and delete.",
    )
    return redirect(f"/{request.user.username}/{project.slug}/")
