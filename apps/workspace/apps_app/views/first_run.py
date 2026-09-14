#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Getting-started checklist endpoints: follow a step, dismiss the panel."""

from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import redirect
from django.views.decorators.http import require_POST

from ..services.first_run import (
    STEPS_BY_KEY,
    dismiss_checklist,
    latest_owned_project,
    mark_step_done,
    step_target_url,
)


def _make_current_project(request, project) -> None:
    from apps.infra.project_app.services.project_utils import set_current_project

    set_current_project(request, project)
    profile = getattr(request.user, "profile", None)
    # Writer and FigRecipe read last_active_repository before the session.
    if profile is not None and profile.last_active_repository_id != project.pk:
        profile.last_active_repository = project
        profile.save(update_fields=["last_active_repository"])


@login_required
def follow_step(request, step_key):
    step = STEPS_BY_KEY.get(step_key)
    if step is None:
        raise Http404("Unknown getting-started step")
    project = latest_owned_project(request.user)
    # Project steps (and step one itself) only complete once a project exists.
    if project is not None or not (step.needs_project or step.key == "create_project"):
        mark_step_done(request.user, step_key)
    if project is not None:
        _make_current_project(request, project)
    return redirect(step_target_url(step_key, request.user, project))


@login_required
@require_POST
def dismiss(request):
    dismiss_checklist(request.user)
    return redirect("/apps/")


# EOF
