#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Create a Work app: a private project scaffolded by ``init_app``.

Thin-hub: the starter catalogue (``STARTERS``, ``STARTERS_BY_KEY``,
``DEFAULT_STARTER``) and ``app_module_name`` live in
``scitex_sdk.creator`` — this module imports them, so the hub copy cannot
drift from the SDK wizard mounted at /create-app/. What stays here is the
hub-domain glue the SDK does not have: turning a request into a private
hub Project (``create_app_project``) plus the presentation overlay for the
fallback create page (``create_page_starters``).
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from types import SimpleNamespace

from django.db import transaction
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

# SSOT — imported, never redefined here. Identity (`is`) with
# `scitex_sdk.creator.STARTERS` is the no-drift guarantee.
from scitex_sdk.creator import (
    DEFAULT_STARTER,
    STARTERS,
    STARTERS_BY_KEY,
    app_module_name,
    starter_brief_section,
)

logger = logging.getLogger(__name__)

APP_SCOPE = "project"
APP_GROUP = "work"

__all__ = [
    "APP_GROUP",
    "APP_SCOPE",
    "DEFAULT_STARTER",
    "STARTERS",
    "STARTERS_BY_KEY",
    "app_module_name",
    "create_app_project",
    "create_page_starters",
]


class AppCreateError(ValueError):
    """The request cannot become an app project; the message is user-facing."""


# Hub-flow presentation copy for the fallback create page. These strings
# describe the HUB workspace flow (a private project, the agent chat, "Run
# privately") which the SDK wizard does not have, so they live here, keyed
# by the SDK starter key — the catalogue itself stays upstream.
_TIME_ESTIMATE = _(
    "Project scaffold: under a minute. First working version with the "
    "agent: typically 5–15 minutes."
)
_BLANK_TIME_ESTIMATE = _(
    "Project scaffold: under a minute. First version depends on your "
    "description; allow extra rounds with the agent."
)
_RESULT = _(
    "Your app workspace at /apps/create/<name>/: the file list, the agent "
    "chat, and a Run privately button that gives you a private test link."
)


def create_page_starters() -> list:
    """Starter cards for the fallback create page.

    The SDK catalogue plus the hub overlay (``time_estimate``/``result``)
    the hub template renders. Labels/hints are re-wrapped in gettext so the
    existing hub catalog entries keep applying; the ``_()`` calls take the
    SDK strings as msgids at runtime (makemessages cannot extract them —
    new SDK copy needs an explicit catalog entry).
    """
    cards = []
    for starter in STARTERS:
        cards.append(
            SimpleNamespace(
                key=starter.key,
                label=_(starter.label),
                hint=_(starter.hint),
                icon=starter.icon,
                brief=starter.brief,
                creates=_(starter.creates),
                builds_first=_(starter.builds_first),
                time_estimate=(
                    _BLANK_TIME_ESTIMATE
                    if starter.key == "blank"
                    else _TIME_ESTIMATE
                ),
                result=_RESULT,
            )
        )
    return cards


def _project_name(label: str) -> str:
    name = re.sub(r"[^a-zA-Z0-9._-]", "-", slugify(label)).strip("-._")
    return name[:90] or "my-app"


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
            fh.write(starter_brief_section(starter, description))
    logger.info("[app_create] %s created app project %s", user.username, slug)
    return project


# EOF
