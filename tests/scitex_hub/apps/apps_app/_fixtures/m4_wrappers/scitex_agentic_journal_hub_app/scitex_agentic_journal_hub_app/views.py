"""Views for Agentic Journal workspace app (user-published, path B)."""

from __future__ import annotations

from django.http import JsonResponse
from django.shortcuts import render

from apps.infra.project_app.services.project_utils import get_current_project


def build_scitex_agentic_journal_hub_app_context(request, current_project=None):
    """Context builder called by workspace registry for AJAX partial loads."""
    return {
        "current_project": current_project,
        "app_name": "Agentic Journal",
        "app_description": "ARA-native open publishing with AI review",
        "features": [
            "Workspace app integration",
            "AJAX partial loading",
            "Scoped CSS with theme variables",
        ],
    }


def index_view(request):
    """Full page view for Agentic Journal."""
    current_project = (
        get_current_project(request) if request.user.is_authenticated else None
    )
    context = build_scitex_agentic_journal_hub_app_context(
        request, current_project=current_project
    )
    return render(request, "scitex_agentic_journal_hub_app/index.html", context)


def submission_log_view(request, paper_id: str):
    """Return the AI-review decision log for ``paper_id``.

    Target of the live-paper ReReviewBadge ``log_url`` (URL shape
    ``/apps/agentic-journal/<paper_id>/log/`` — matches the live-paper
    hub app's wiring in ``scitex_live_paper_hub_app/urls.py``).

    Delegates to the upstream ``scitex_agentic_journal`` package so
    schema / formatting stays single-sourced. Hub app is a thin
    surface only.
    """
    from scitex_agentic_journal import load_submission_log

    log = load_submission_log(paper_id)
    if log is None:
        return JsonResponse(
            {"error": f"no submission log for paper {paper_id!r}"},
            status=404,
        )
    return JsonResponse(log)


# EOF
