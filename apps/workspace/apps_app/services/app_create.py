#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Create a Work app: a private project scaffolded by ``init_app``.

Starters are not separate scaffolds. Each one is a short brief layered over
the same html template: it lands in the manifest's ``ai_hint`` and in an
extra AGENTS.md section, so the app-maker agent knows what to build first.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path

from django.db import transaction
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from django.utils.translation import override

logger = logging.getLogger(__name__)

APP_SCOPE = "project"
APP_GROUP = "work"


@dataclass(frozen=True)
class Starter:
    """One card on the create page.

    brief is the internal build instruction for the agent. creates,
    builds_first, time_estimate and result are the plain-language
    card copy: what gets created, what the agent builds first, how long it
    takes, and where the result appears.
    """

    key: str
    label: str
    hint: str
    icon: str
    brief: str
    creates: str = ""
    builds_first: str = ""
    time_estimate: str = ""
    result: str = ""


_TIME_ESTIMATE = _(
    "Project scaffold: under a minute. First working version with the "
    "agent: typically 5–15 minutes."
)
_RESULT = _(
    "Your app workspace at /apps/create/<name>/: the file list, the agent "
    "chat, and a Run privately button that gives you a private test link."
)

STARTERS: tuple[Starter, ...] = (
    Starter(
        "data_entry",
        _("Data entry form"),
        _("Record trials, samples or observations into the project."),
        "fas fa-table-list",
        "Build a data entry form for one experiment. Each submission appends a "
        "row to a CSV file under the project's data/ directory. Validate "
        "required fields and show the latest rows under the form.",
        creates=_(
            "A private app project with a data-entry form scaffold: an input "
            "form, required-field validation, answers saved as CSV rows under "
            "the project's data/ folder, and the latest rows shown under the "
            "form."
        ),
        builds_first=_(
            "A form for one experiment. Each submission appends a row to a "
            "CSV file under data/, with validation and recent rows visible."
        ),
        time_estimate=_TIME_ESTIMATE,
        result=_RESULT,
    ),
    Starter(
        "dashboard",
        _("Analysis dashboard"),
        _("Summarise and plot result files from the project."),
        "fas fa-chart-line",
        "Build an analysis dashboard. List CSV result files in the project, "
        "let the user pick one, and show summary statistics and a simple plot.",
        creates=_(
            "A private app project with an analysis-dashboard scaffold: a "
            "result-file picker, summary statistics, and a simple plot of the "
            "selected CSV file."
        ),
        builds_first=_(
            "A dashboard that lists CSV result files in the project and shows "
            "summary statistics plus a plot for the chosen file."
        ),
        time_estimate=_TIME_ESTIMATE,
        result=_RESULT,
    ),
    Starter(
        "log_viewer",
        _("Device/log viewer"),
        _("Browse and filter instrument logs or recordings."),
        "fas fa-wave-square",
        "Build a device/log viewer. List log or recording files in the project, "
        "open one, and let the user scroll, search and filter its lines or "
        "samples by time.",
        creates=_(
            "A private app project with a log-viewer scaffold: a file list to "
            "open one log or recording, then scroll, search, and filter its "
            "lines or samples by time."
        ),
        builds_first=_(
            "A viewer that lists log or recording files, opens one, and lets "
            "you scroll, search, and filter by time."
        ),
        time_estimate=_TIME_ESTIMATE,
        result=_RESULT,
    ),
    Starter(
        "blank",
        _("Blank"),
        _("Start from the plain template and describe it to the agent."),
        "fas fa-puzzle-piece",
        "Start from the plain template; build what the description asks for.",
        creates=_(
            "A private app project with the plain template only — no "
            "pre-built feature. The agent builds whatever your description "
            "asks for."
        ),
        builds_first=_(
            "Whatever your description above asks for, starting from the "
            "plain template."
        ),
        time_estimate=_(
            "Project scaffold: under a minute. First version depends on your "
            "description; allow extra rounds with the agent."
        ),
        result=_RESULT,
    ),
)

STARTERS_BY_KEY = {s.key: s for s in STARTERS}
DEFAULT_STARTER = "blank"


class AppCreateError(ValueError):
    """The request cannot become an app project; the message is user-facing."""


def app_module_name(slug: str) -> str:
    name = re.sub(r"[^a-z0-9_]", "_", slug.lower()).strip("_") or "my"
    if name[0].isdigit():
        name = f"app_{name}"
    return name if name.endswith("_app") else f"{name}_app"


def _project_name(label: str) -> str:
    name = re.sub(r"[^a-zA-Z0-9._-]", "-", slugify(label)).strip("-._")
    return name[:90] or "my-app"


def _agents_md_section(starter: Starter, description: str) -> str:
    with override("en"):
        return _agents_md_text(starter, description)


def _agents_md_text(starter: Starter, description: str) -> str:
    return (
        "\n\n## What the user asked for\n\n"
        f"Starter: **{starter.label}**\n\n"
        f"{starter.brief}\n\n"
        f"User's description: {description or '(none yet — ask them)'}\n\n"
        "This is a **Work app** for an experiment. It is project-scoped "
        '(`"scope": "project"` in manifest.json): it reads and writes files of '
        "the project the user opens it in, never other users' data.\n"
    )


def create_app_project(user, label: str, description: str, starter_key: str):
    """Create a private app project for ``user`` and scaffold it.

    Returns the Project. Raises AppCreateError for bad input.
    """
    from apps.infra.project_app.models import Project
    from apps.infra.project_app.services.filesystem.manager import (
        get_project_filesystem_manager,
    )
    from scitex_hub.appmaker import init_app

    label = (label or "").strip()
    description = (description or "").strip()
    if not label:
        raise AppCreateError(_("Give your app a name."))
    starter = STARTERS_BY_KEY.get(starter_key)
    if starter is None:
        raise AppCreateError(_("Pick a starter template."))

    name = _project_name(label)
    slug = Project.generate_unique_slug(name, owner=user)
    with transaction.atomic():
        # is_app at create time: the post_save clone skips writer/scholar setup.
        project = Project.objects.create(
            name=slug,
            slug=slug,
            description=description[:500],
            owner=user,
            visibility="private",
            is_app=True,
            app_status="draft",
        )
    manager = get_project_filesystem_manager(user)
    ok, path = manager.create_project_directory(project, use_template=False)
    if not ok or path is None:
        project.delete()
        raise AppCreateError(_("Could not create the project directory."))

    project_dir = Path(path)
    module = app_module_name(slug)
    init_app(
        target_dir=str(project_dir),
        name=module,
        # init_app derives a Python class name from the label; keep that one identifier-safe.
        label=re.sub(r"[^\w ]", " ", label).strip() or "My",
        icon=starter.icon,
        description=description,
        manifest={
            "label": label,
            "author": user.get_full_name() or user.username,
            "scope": APP_SCOPE,
            "group": APP_GROUP,
            "starter": starter.key,
            "ai_hint": f"{starter.brief} {description}".strip(),
        },
    )
    agents_md = project_dir / "AGENTS.md"
    if agents_md.is_file():
        with agents_md.open("a", encoding="utf-8") as fh:
            fh.write(_agents_md_section(starter, description))
    logger.info("[app_create] %s created app project %s", user.username, slug)
    return project


# EOF
