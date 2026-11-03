"""Template context shared by project pages."""

from django.conf import settings
from django.urls import Resolver404, resolve

from apps.infra.project_app.models import Project


def version_context(request):
    """Add the SciTeX Hub version to every template."""
    return {
        "SCITEX_HUB_VERSION": getattr(settings, "SCITEX_HUB_VERSION", "0.1.0-alpha"),
    }


def project_context(request):
    """Resolve URL project context without manufacturing an anonymous identity."""
    project = None
    # Native apps also have two path segments. Ask the URL owner instead of
    # interpreting /apps/live-paper/ (or /accounts/settings/) as a repository.
    match = getattr(request, "resolver_match", None)
    if match is None:
        try:
            match = resolve(request.path_info)
        except Resolver404:
            match = None
    if match is not None and "project_app" in match.app_names:
        username = match.kwargs.get("username")
        project_slug = match.kwargs.get("slug")
        if username and project_slug:
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
