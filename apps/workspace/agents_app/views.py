"""Authentication boundary for SAC's read-only dashboard."""

from django.contrib.auth.decorators import login_required


@login_required
def index(request):
    from scitex_agent_container._django.views import index as upstream

    return upstream(request)


@login_required
def fleet_api(request):
    from scitex_agent_container._django.views import fleet_api as upstream

    return upstream(request)


@login_required
def healthz(request):
    from scitex_agent_container._django.views import healthz as upstream

    return upstream(request)


@login_required
def detail(request, name: str):
    from scitex_agent_container._django.views import detail as upstream

    return upstream(request, name)


@login_required
def lifecycle_action(request, name: str):
    from scitex_agent_container._django.views import lifecycle_action as upstream

    return upstream(request, name)
