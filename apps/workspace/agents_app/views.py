"""Login-gated delegates to the optional SAC Django dashboard.

Imports stay inside each call because scitex-agent-container is an optional
sibling. A Hub installation without it must still import settings, collect
tests, and serve every unrelated app; config/urls.py omits this mount in that
case.
"""

from __future__ import annotations

from django.contrib.auth.decorators import login_required


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
