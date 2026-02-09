"""
Verifier - Views Package
"""

from django.shortcuts import render

from apps.project_app.services.project_utils import get_current_project

from . import api


def verifier_index(request):
    """Main verifier view - DAG visualization for reproducibility verification

    Shows verification chain for tracing claims back to source data.
    """
    context = {
        "module_name": "Verifier",
        "module_icon": "fa-check-circle",
    }

    # Get current project from header dropdown
    if request.user.is_authenticated:
        current_project = get_current_project(request, user=request.user)

        if current_project:
            context["current_project"] = current_project
            context["project"] = current_project
        else:
            context["needs_project_creation"] = True

    return render(request, "verifier_app/index.html", context)


__all__ = ["verifier_index", "api"]
