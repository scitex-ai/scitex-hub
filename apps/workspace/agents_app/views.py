"""Authenticated Hub adapters for SAC's leaf-owned dashboard views."""

import os
from functools import wraps

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden


def _fleet_access_allowed(request) -> bool:
    user = request.user
    configured = {
        value.strip()
        for value in os.environ.get(
            "SCITEX_AGENT_CONTAINER_LIFECYCLE_OPERATORS", ""
        ).split(",")
        if value.strip()
    }
    return bool(
        user.is_superuser
        or user.is_staff
        or getattr(user, "username", "") in configured
    )


def _fleet_access_required(view):
    @wraps(view)
    def guarded(request, *args, **kwargs):
        if not _fleet_access_allowed(request):
            return HttpResponseForbidden(
                "This account is not a SAC fleet operator."
            )
        return view(request, *args, **kwargs)

    return guarded


@login_required
@_fleet_access_required
def index(request):
    from scitex_agent_container._django.views import index as upstream

    return upstream(request)


@login_required
@_fleet_access_required
def fleet_api(request):
    from scitex_agent_container._django.views import fleet_api as upstream

    return upstream(request)


@login_required
@_fleet_access_required
def healthz(request):
    from scitex_agent_container._django.views import healthz as upstream

    return upstream(request)


@login_required
@_fleet_access_required
def detail(request, name: str):
    from scitex_agent_container._django.views import detail as upstream

    return upstream(request, name)


@login_required
def lifecycle_action(request, name: str):
    from scitex_agent_container._django.views import lifecycle_action as upstream

    return upstream(request, name)
