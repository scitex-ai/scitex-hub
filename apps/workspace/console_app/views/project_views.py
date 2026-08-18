"""
Project-specific views for Code app.
"""

from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import render, get_object_or_404
from apps.infra.project_app.models import Project


@login_required
def project_code(request, project_id):
    """Code interface for a specific project."""
    project = get_object_or_404(Project, id=project_id)

    # Tenant isolation: the id comes straight off the URL, so the fetch alone
    # proves nothing. Gate access to the project's code interface on ownership
    # (same owner/collaborator/public rule as file_content.py) — otherwise any
    # authenticated user could open ANY tenant's project by iterating the id
    # (cross-tenant IDOR). 404 (not 403) so it doesn't confirm the id exists.
    if not (
        request.user == project.owner
        or request.user in project.collaborators.all()
        or project.visibility == "public"
    ):
        raise Http404("Project not found")

    context = {
        "project": project,
    }
    return render(request, "console_app/project_code.html", context)
