"""The SDK project picker's HTTP provider: ``/api/project/scope/``.

Serves the SDK ``scoped_project_listing_view`` contract through the hub's
``HubProjectProvider`` (which offers the optional tagged-scope
capability): GET advertises ``allow_user_scope`` + ``current_scope``,
POST accepts the legacy ``{"id"}`` shape and the explicit
``{"scope", "id"}`` pair (403 when not accessible).
"""

from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods

from apps.infra.project_app.services.project_scope import HubProjectProvider


@login_required
@require_http_methods(["GET", "POST"])
def api_project_scope(request):
    from scitex_sdk.ui.project_scope import scoped_project_listing_view

    return scoped_project_listing_view(lambda _request: HubProjectProvider())(
        request
    )
