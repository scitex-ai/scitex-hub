"""Template context shared by project pages."""

import re

from django.conf import settings

from apps.infra.project_app.models import Project


def version_context(request):
    """Add the SciTeX Hub version to every template."""
    return {
        "SCITEX_HUB_VERSION": getattr(settings, "SCITEX_HUB_VERSION", "0.1.0-alpha"),
    }


def project_context(request):
    """Resolve URL project context without manufacturing an anonymous identity."""
    project = None
    match = re.match(r"^/([^/]+)/([^/]+)/", request.path)
    if match:
        username, project_slug = match.groups()
        try:
            project = Project.objects.select_related("owner").get(
                owner__username=username,
                slug=project_slug,
            )
        except Project.DoesNotExist:
            pass

    if request.user.is_authenticated:
        default_project_url = f"/{request.user.username}/default"
    else:
        default_project_url = "/auth/signup/"

    return {
        "project": project,
        "guest_project_url": default_project_url,
        "default_project_url": default_project_url,
        "is_guest_session": False,
    }
