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
from django.http import HttpResponseForbidden

# Login alone is not enough. SAC's own views gate only lifecycle_action on
# its operator list; index, fleet_api, healthz and detail have no check, so a
# login-only adapter shows the whole agent fleet to every signed-in Hub user
# (the same exposure the Cards mount had, fixed in #805). Restored from #789.
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
@_fleet_access_required
def index(request):
    return _delegate("index", request)


@login_required
@_fleet_access_required
def fleet_api(request):
    return _delegate("fleet_api", request)


@login_required
@_fleet_access_required
def healthz(request):
    return _delegate("healthz", request)


@login_required
@_fleet_access_required
def detail(request, name):
    return _delegate("detail", request, name=name)


@login_required
@_fleet_access_required
def lifecycle_action(request, name):
    return _delegate("lifecycle_action", request, name=name)


__all__ = ["detail", "fleet_api", "healthz", "index", "lifecycle_action"]
