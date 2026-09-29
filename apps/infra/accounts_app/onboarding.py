#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""First-login project choice — the user picks the project, never the code.

Card: hub-first-login-project-workspace-onboarding-20260917.
SSOT: docs/product/PRIVATE_BETA_LOGIN_TO_WOW.md §3 ("The primary action is
**Create project**… The sample exists only after explicit selection") and the
non-negotiable rule "Real users never receive a silently created or selected
example project."

Why this module exists rather than a flag at each call site: two places used to
manufacture a choice — ``accounts_app.signals`` adopted the dotfiles/oldest
project on user creation and on every login, and
``UserProfile.get_active_project()`` picked and persisted the first owned
project on read. A single pure rule keeps the answer identical everywhere:
**no explicit choice means no active project.** A user who has chosen nothing
gets the first-login welcome, not somebody else's idea of their project.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional, Union

from django.utils.functional import Promise
from django.utils.translation import gettext_lazy as _

# Stable keys — addressable by tests, JS and the video pipeline. Never
# translated; the label is what a human reads.
CREATE_PROJECT = "create-project"
IMPORT_PROJECT_OR_FILES = "import-project"
GUIDED_SAMPLE = "guided-sample"


@dataclass(frozen=True)
class FirstLoginAction:
    """One explicit choice on the first-login welcome."""

    key: str
    label: Union[str, Promise]
    is_primary: bool = False
    #: Nothing may run before the user clicks it — the guided sample in
    #: particular must never be created by page load.
    is_preselected: bool = False


ACTIONS: tuple[FirstLoginAction, ...] = (
    FirstLoginAction(CREATE_PROJECT, _("Create project"), is_primary=True),
    FirstLoginAction(IMPORT_PROJECT_OR_FILES, _("Import project or files")),
    FirstLoginAction(GUIDED_SAMPLE, _("Use a guided sample")),
)


def first_login_actions() -> tuple[FirstLoginAction, ...]:
    """The three explicit choices, in order, with at most one primary."""
    return ACTIONS


def needs_project_choice(*, has_explicit_choice: bool) -> bool:
    """Whether the workspace must ask before it can show a project.

    True when the user has never chosen one. Note the deliberate asymmetry:
    an empty workspace is a question to ask, not a gap to fill in.
    """
    return not has_explicit_choice


def profile_has_explicit_choice(profile) -> bool:
    """Whether ``profile`` records a project the user actually chose.

    Reading the stored id (not the related object) keeps this callable from
    templates and cheap enough to run on every page: it triggers no query.
    """
    return bool(getattr(profile, "last_active_repository_id", None))


def resolve_active_project(
    projects: Iterable, chosen_project_id: Optional[int] = None
):
    """Return the project to show, or ``None`` when the user has not chosen.

    ``projects`` is whatever the caller already loaded (the profile-owned set).
    An explicit choice wins; a choice the user does not own is ignored rather
    than silently replaced. With no choice — or no match — the answer is
    ``None``: the caller then asks instead of guessing, so a dotfiles or
    example project can never become active on its own.
    """
    if chosen_project_id is None:
        return None
    for project in projects:
        if getattr(project, "pk", None) == chosen_project_id:
            return project
    return None


#: Workspace facts stated on the first-login welcome. Values are the platform's
#: own: one stable Linux identity per account, and the NAS-02-backed persistent
#: workspace quota. Storage — not RAM — because that is the misconception the
#: welcome exists to prevent.
WORKSPACE_HOST = "NAS-02"
WORKSPACE_GB = 32

#: `/new/` is the canonical, already-shipped project-creation page, and it is a
#: TABBED page that includes the import-from-Git/files tab. The welcome links to
#: the real destination instead of re-implementing creation.
_CREATE_PROJECT_URL_NAME = "project_create"

#: POST-only endpoint that provisions the guided sample after the user's
#: explicit click (SSOT docs/product/PRIVATE_BETA_LOGIN_TO_WOW.md §3).
_GUIDED_SAMPLE_URL_NAME = "guided_sample_create"


def _url_or_empty(name: str) -> str:
    """Reverse ``name``, or "" when the route is not present in this deploy."""
    from django.urls import NoReverseMatch, reverse

    try:
        return reverse(name)
    except NoReverseMatch:
        return ""


def first_login_context(profile=None) -> dict:
    """Template context for the first-login welcome.

    Kept next to the rule so the surface and the decision cannot disagree about
    what "no project chosen" means.
    """
    create_url = _url_or_empty(_CREATE_PROJECT_URL_NAME)
    guided_url = _url_or_empty(_GUIDED_SAMPLE_URL_NAME)
    entries = []
    for action in ACTIONS:
        if action.key in (CREATE_PROJECT, IMPORT_PROJECT_OR_FILES):
            # `/new/` is the unified tabbed creation page and includes the
            # import tab, so both choices point at the shipped destination
            # rather than re-implementing creation here.
            entries.append(
                {
                    "key": action.key,
                    "label": action.label,
                    "is_primary": action.is_primary,
                    "is_preselected": action.is_preselected,
                    "url": create_url,
                    "available": bool(create_url),
                }
            )
        elif action.key == GUIDED_SAMPLE:
            # POST-only: provisioning runs after the explicit click, never
            # on page load. The template renders this as a form button.
            entries.append(
                {
                    "key": action.key,
                    "label": action.label,
                    "is_primary": action.is_primary,
                    "is_preselected": action.is_preselected,
                    "url": guided_url,
                    "available": bool(guided_url),
                    "method": "post",
                }
            )
        else:
            # Unknown future action: explicit unavailable state rather than
            # a control that silently does nothing.
            entries.append(
                {
                    "key": action.key,
                    "label": action.label,
                    "is_primary": action.is_primary,
                    "is_preselected": action.is_preselected,
                    "url": "",
                    "available": False,
                }
            )
    return {
        "actions": entries,
        "workspace_host": WORKSPACE_HOST,
        "workspace_gb": WORKSPACE_GB,
        "active_project": None,
    }


# EOF
