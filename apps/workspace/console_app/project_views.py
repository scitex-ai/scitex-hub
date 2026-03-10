"""
Project-specific views for Code app.
"""

from django.shortcuts import render, get_object_or_404
from apps.infra.project_app.models import Project


def project_code(request, project_id):
    """Code interface for a specific project."""
    project = get_object_or_404(Project, id=project_id)

    context = {
        "project": project,
    }
    return render(request, "console_app/project_code.html", context)
