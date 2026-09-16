"""Authenticated delegates to SAC's identity-scoped Django dashboard.

The Hub owns authentication.  SAC owns row scoping and lifecycle authorization;
passing the original request is essential because SAC resolves the acting
identity from ``request.user``.  Imports remain lazy because SAC is optional.
"""

from __future__ import annotations

import os

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils.translation import gettext_lazy as _

OPERATORS_ENV = "SCITEX_AGENT_CONTAINER_LIFECYCLE_OPERATORS"


def _fleet_access_allowed(user) -> bool:
    """Legacy operator predicate retained for the separately gated Cards app."""
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
    }
}


def own_scope_placeholder(request, app_slug):
    """Render the held Cards surface without exposing board data."""
    return render(
        request,
        "fleet_apps/own_scope_coming_soon.html",
        {"app_slug": app_slug, **_PLACEHOLDER_APPS[app_slug]},
    )


def _delegate(view_name, request, *args, **kwargs):
    from scitex_agent_container._django import views as upstream

    return getattr(upstream, view_name)(request, *args, **kwargs)


@login_required
def index(request):
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


@login_required
def lifecycle_action(request, name):
    return _delegate("lifecycle_action", request, name=name)


__all__ = ["detail", "fleet_api", "healthz", "index", "lifecycle_action"]
