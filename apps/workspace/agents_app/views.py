"""Login-gated delegates to the optional SAC Django dashboard.

Imports stay inside each call because scitex-agent-container is an optional
sibling. A Hub installation without it must still import settings, collect
tests, and serve every unrelated app; config/urls.py omits this mount in that
case.
"""

from __future__ import annotations

import os
from functools import wraps

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, HttpResponseNotFound
from django.shortcuts import render
from django.utils.translation import gettext_lazy as _

# Reads are login-only: scitex-agent-container >= 0.28 scopes EVERY read by
# identity itself (resolve_identity + scope_rows in each view; the snapshot
# cache is keyed per identity), so an ordinary signed-in user only ever sees
# their own agents. Mutations stay operator-gated twice: the hub decorator
# below AND upstream can_control() on lifecycle/message actions. (#789 gate
# lifted 2026-09-26 once upstream scoping was verified.)
OPERATORS_ENV = "SCITEX_AGENT_CONTAINER_LIFECYCLE_OPERATORS"


def _fleet_access_allowed(user) -> bool:
    configured = {
        value.strip()
        for value in os.environ.get(OPERATORS_ENV, "").split(",")
        if value.strip()
    }
    return bool(
        getattr(user, "is_superuser", False)
        or getattr(user, "is_staff", False)
        or getattr(user, "username", "") in configured
    )


_PLACEHOLDER_APPS = {
    "cards": {
        "app_label": _("Cards"),
        "app_icon": "fa-list-check",
        "lead": _("Your own cards will appear here."),
    },
    "agents": {
        "app_label": _("Agents"),
        "app_icon": "fa-robot",
        "lead": _("Your own agents will appear here."),
    },
}


def own_scope_placeholder(request, app_slug):
    """Friendly page for a signed-in user the app cannot scope content to yet.

    Operator 2026-09-14: Cards and Agents are shown to everyone and only their
    content depends on the user. Until each app filters its data per user, the
    page says so and shows none of the fleet's data.
    """
    return render(
        request,
        "fleet_apps/own_scope_coming_soon.html",
        {"app_slug": app_slug, **_PLACEHOLDER_APPS[app_slug]},
    )


def _fleet_access_required(view):
    @wraps(view)
    def guarded(request, *args, **kwargs):
        if not _fleet_access_allowed(request.user):
            return HttpResponseForbidden("This account is not a SAC fleet operator.")
        return view(request, *args, **kwargs)

    return guarded


def _delegate(view_name, request, *args, **kwargs):
    from scitex_agent_container._django import views as upstream

    return getattr(upstream, view_name)(request, *args, **kwargs)


@login_required
def index(request):
    # Upstream scopes rows to this user's identity; no hub-side gate.
    return _delegate("index", request)


@login_required
def fleet_api(request):
    return _delegate("fleet_api", request)


@login_required
def healthz(request):
    return _delegate("healthz", request)


@login_required
def detail(request, name):
    return _delegate("detail", request, name=name)


# Control plane: stays operator-gated at the hub boundary (upstream
# can_control() gates it a second time).
@login_required
@_fleet_access_required
def lifecycle_action(request, name):
    return _delegate("lifecycle_action", request, name=name)


# Agent CREATE (upstream scitex-agent-container#1528): start a pre-registered
# spec by name. Operator-gated here and by upstream can_control(). Returns
# 404 until the installed upstream release carries views.launch.
@login_required
@_fleet_access_required
def launch(request):
    from scitex_agent_container._django import views as upstream

    if not hasattr(upstream, "launch"):
        return HttpResponseNotFound("Agent launch is not in this release yet.")
    return _delegate("launch", request)


__all__ = ["detail", "fleet_api", "healthz", "index", "launch", "lifecycle_action"]
