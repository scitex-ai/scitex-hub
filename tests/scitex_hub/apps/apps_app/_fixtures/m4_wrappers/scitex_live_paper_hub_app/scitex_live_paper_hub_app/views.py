"""Views for Live Paper workspace app (user-published, path B)."""

from __future__ import annotations

from typing import Any

from django.shortcuts import render

from apps.infra.project_app.services.project_utils import get_current_project


def build_scitex_live_paper_hub_app_context(request, current_project=None):
    """Context builder called by workspace registry for AJAX partial loads."""
    return {
        "current_project": current_project,
        "app_name": "Live Paper",
        "app_description": "Interactive paper viewer with M4 re-review chip",
        "features": [
            "Workspace app integration",
            "AJAX partial loading",
            "Scoped CSS with theme variables",
        ],
    }


def index_view(request):
    """Full page view for Live Paper."""
    current_project = (
        get_current_project(request) if request.user.is_authenticated else None
    )
    context = build_scitex_live_paper_hub_app_context(
        request, current_project=current_project
    )
    return render(request, "scitex_live_paper_hub_app/index.html", context)


def load_paper(paper_id: str, project_id: int) -> Any:
    """Load a paper's bundle source for the live-paper renderer.

    Delegates to ``apps.infra.project_app.services`` to resolve the on-
    disk paper path for the given project, then returns the bytes the
    :class:`scitex_live_paper.BundleSource` can stream. Implemented per
    the operator-owned project's storage convention
    (``<project>/papers/<paper_id>/bundle.zip`` today; subject to
    project_app evolution).

    Raises FileNotFoundError loudly if the paper is missing — the
    no-silent-fallback rule applies. The renderer surfaces the 404 to
    the user.
    """
    from pathlib import Path

    from apps.infra.project_app.models import Project

    project = Project.objects.get(id=project_id)
    paper_dir = Path(project.data_dir) / "papers" / paper_id
    bundle = paper_dir / "bundle.zip"
    if not bundle.is_file():
        raise FileNotFoundError(
            f"paper {paper_id!r} not found in project {project.slug!r} "
            f"at {bundle} (run `scitex-hub paper sync {paper_id}` first?)"
        )
    return bundle.read_bytes()


# EOF
