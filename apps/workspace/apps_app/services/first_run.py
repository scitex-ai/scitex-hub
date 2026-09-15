#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The Home "Getting started" checklist: steps, targets and per-user progress."""

from __future__ import annotations

import os
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


def _owned_projects(user):
    from apps.infra.project_app.models import Project

    # Every account already owns a home (dotfiles) project; it is not "your first project".
    return (
        Project.objects.filter(owner=user, is_home=False)
        .exclude(slug="dotfiles")
        .order_by("-created_at")
    )


def latest_owned_project(user):
    return _owned_projects(user).first()


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


def dismiss_checklist(user, forever: bool = False) -> FirstRunProgress:
    progress = progress_for(user)
    now = timezone.now()
    fields = []
    if progress.dismissed_at is None:
        progress.dismissed_at = now
        fields.append("dismissed_at")
    if forever and progress.hidden_at is None:
        progress.hidden_at = now
        fields.append("hidden_at")
    if fields:
        progress.save(update_fields=[*fields, "updated_at"])
    return progress


def reshow_checklist(user) -> FirstRunProgress:
    progress = progress_for(user)
    progress.dismissed_at = None
    progress.hidden_at = None
    progress.reshown_at = timezone.now()
    progress.save(update_fields=["dismissed_at", "hidden_at", "reshown_at", "updated_at"])
    return progress


def should_show_checklist(user) -> bool:
    progress = FirstRunProgress.objects.filter(user=user).only(
        "hidden_at", "reshown_at"
    ).first()
    if progress is not None and progress.hidden_at is not None:
        return False
    return is_new_user(user) or (progress is not None and progress.reshown_at is not None)


# Only the newest few projects are looked at on disk, to keep Home cheap.
_PROJECTS_SCANNED = 3
_SAMPLE_FIGURE_STEM = "sample_plot"


def _project_root(project):
    from pathlib import Path

    from apps.infra.project_app.services.filesystem.paths import get_project_root_path

    if project.local_path:
        path = Path(project.local_path)
        return path if path.is_dir() else None
    return get_project_root_path(project.owner, project)


def _has_own_figure(root) -> bool:
    # A FigRecipe figure is a recipe YAML with its rendered PNG beside it.
    for folder in (root, root / "figures"):
        try:
            names = {entry.name for entry in os.scandir(folder) if entry.is_file()}
        except OSError:
            continue
        for name in names:
            stem, ext = os.path.splitext(name)
            if ext == ".yaml" and stem != _SAMPLE_FIGURE_STEM and f"{stem}.png" in names:
                return True
    return False


def _has_compiled_manuscript(root) -> bool:
    from apps.infra.project_app.services.writer_workspace_layout import (
        get_compiled_pdf_path,
        get_writer_workspace_path,
    )

    if get_compiled_pdf_path(root).is_file():
        return True
    preview_dir = get_writer_workspace_path(root) / ".preview"
    return preview_dir.is_dir() and any(preview_dir.glob("*.pdf"))


def _has_references(user) -> bool:
    from apps.workspace.scholar_app.models import BibTeXEnrichmentJob, UserLibrary

    return (
        UserLibrary.objects.filter(user=user).exists()
        or BibTeXEnrichmentJob.objects.filter(user=user).exists()
    )


def _has_asked_agent(user) -> bool:
    from apps.infra.llm_app.models import ChatMessage

    return ChatMessage.objects.filter(session__user=user, role="user").exists()


def derived_completed_steps(user, projects) -> set[str]:
    """Steps the user has visibly done, read from real data (no tracking of its own)."""
    done = set()
    if projects:
        done.add("create_project")
    roots = [root for root in map(_project_root, projects) if root is not None]
    if any(_has_own_figure(root) for root in roots):
        done.add("make_figure")
    if any(_has_compiled_manuscript(root) for root in roots):
        done.add("draft_manuscript")
    if _has_references(user):
        done.add("add_references")
    if _has_asked_agent(user):
        done.add("ask_agent")
    return done


def checklist_context(user) -> dict:
    """Template context for the checklist: real activity, or the stored mark as a fallback."""
    progress = progress_for(user)
    projects = list(_owned_projects(user)[:_PROJECTS_SCANNED])
    done_keys = derived_completed_steps(user, projects) | set(progress.completed_steps)
    steps = [
        {
            "number": index,
            "key": step.key,
            "label": step.label,
            "done": step.key in done_keys,
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
        "storage_key": f"scitex.firstRun.open.{user.pk}",
    }


# EOF
