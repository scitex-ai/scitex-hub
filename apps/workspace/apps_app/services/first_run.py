#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The Home "Getting started" checklist: steps, targets and per-user progress."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from urllib.parse import urlencode

from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from ..models import FirstRunProgress

SUGGESTED_AGENT_PROMPT = (
    "Summarise data/sample.csv and add a Results paragraph to the manuscript."
)


@dataclass(frozen=True)
class FirstRunStep:
    key: str
    label: str
    needs_project: bool


STEPS = (
    FirstRunStep("create_project", _("Create your first project"), False),
    FirstRunStep("open_sample_data", _("Open the sample data"), True),
    FirstRunStep("make_figure", _("Make a figure"), True),
    FirstRunStep("draft_manuscript", _("Draft your manuscript"), True),
    FirstRunStep("add_references", _("Add references"), False),
    FirstRunStep("ask_agent", _("Ask the AI agent"), False),
)
STEP_KEYS = tuple(step.key for step in STEPS)
STEPS_BY_KEY = {step.key: step for step in STEPS}
NEW_USER_WINDOW = timedelta(days=30)


def is_new_user(user) -> bool:
    return user.date_joined >= timezone.now() - NEW_USER_WINDOW


def latest_owned_project(user):
    from apps.infra.project_app.models import Project

    # Every account already owns a home (dotfiles) project; it is not "your first project".
    return (
        Project.objects.filter(owner=user, is_home=False).order_by("-created_at").first()
    )


def step_target_url(step_key: str, user, project) -> str:
    if step_key == "create_project":
        return "/new/"
    if step_key == "add_references":
        return "/apps/scholar/"
    if step_key == "ask_agent":
        return "/chat/?" + urlencode({"prompt": SUGGESTED_AGENT_PROMPT})
    if project is None:
        return "/new/"
    if step_key == "open_sample_data":
        return f"/{user.username}/{project.slug}/data/"
    if step_key == "make_figure":
        return f"/apps/figrecipe/?project={project.slug}"
    return f"/apps/writer/?project={project.slug}"


def progress_for(user) -> FirstRunProgress:
    progress, _created = FirstRunProgress.objects.get_or_create(user=user)
    return progress


def mark_step_done(user, step_key: str) -> FirstRunProgress:
    progress = progress_for(user)
    if step_key in STEP_KEYS and step_key not in progress.completed_steps:
        progress.completed_steps[step_key] = timezone.now().isoformat()
        progress.save(update_fields=["completed_steps", "updated_at"])
    return progress


def dismiss_checklist(user) -> FirstRunProgress:
    progress = progress_for(user)
    if progress.dismissed_at is None:
        progress.dismissed_at = timezone.now()
        progress.save(update_fields=["dismissed_at", "updated_at"])
    return progress


def checklist_context(user) -> dict:
    """Template context for the checklist; auto-completes step one from real projects."""
    project = latest_owned_project(user)
    progress = (
        mark_step_done(user, "create_project") if project else progress_for(user)
    )
    steps = [
        {
            "number": index,
            "key": step.key,
            "label": step.label,
            "done": step.key in progress.completed_steps,
            "url": f"/apps/getting-started/{step.key}/",
        }
        for index, step in enumerate(STEPS, start=1)
    ]
    done_count = sum(1 for step in steps if step["done"])
    return {
        "steps": steps,
        "done_count": done_count,
        "total_count": len(steps),
        "is_collapsed": progress.dismissed_at is not None or done_count == len(steps),
    }


# EOF
