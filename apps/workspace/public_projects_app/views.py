#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Public Projects App views — public repo and user public projects workspace module."""

import logging

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Count
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.views.decorators.http import require_http_methods

from apps.infra.project_app.models import Project

logger = logging.getLogger(__name__)


def build_public_projects_context(request, current_project=None):
    """Context builder for the public projects workspace module (repositories tab default)."""
    repositories = (
        Project.objects.filter(visibility="public")
        .annotate(star_count=Count("stars"))
        .select_related("owner", "owner__profile")
        .order_by("-star_count", "-updated_at")[:20]
    )

    dev_installed_set = set()
    if request.user.is_authenticated:
        try:
            from apps.workspace.apps_app.models import DevInstallation

            dev_installed_set = set(
                DevInstallation.objects.filter(user=request.user).values_list(
                    "source_owner", "source_repo"
                )
            )
        except Exception:
            pass

    return {
        "tab": "repositories",
        "repositories": repositories,
        "dev_installed_set": dev_installed_set,
        "current_project": current_project,
        # Signed-out visitors browse the listing read-only: no Users /
        # Organizations tabs (their API is sign-in only) and no Private Install.
        "public_projects_read_only": not request.user.is_authenticated,
    }


@require_http_methods(["GET"])
def public_projects_index(request):
    """GET /apps/public-projects/ — Public Projects, one pane.

    This used to mount the legacy three-pane workspace shell: a left AI chat
    pane ("Ask anything about Scientific Research"), an unrelated, mostly
    empty project file pane, and the listing loaded over AJAX on the right.
    Operator 2026-09-14: one pane, in the same list/tree look as My Projects.
    The page renders the listing server-side inside the ordinary workspace
    page (module pane), so there is no second shell and no loading flash.
    Signed-out visitors get the same listing, read-only (site audit
    2026-09-14, D11: they used to be bounced to /landing/). Every row links to
    /<owner>/<slug>/, which already serves public projects to anonymous
    visitors read-only (#814).
    """
    from django.shortcuts import render

    return render(
        request, "public_projects_app/index.html", build_public_projects_context(request)
    )


@login_required
@require_http_methods(["GET"])
def api_explore(request):
    """GET /public-projects/api/explore/?tab=repositories|users|groups — tab content."""
    tab = request.GET.get("tab", "repositories")
    context = {"tab": tab}

    if tab == "repositories":
        repositories = (
            Project.objects.filter(visibility="public")
            .annotate(star_count=Count("stars"))
            .select_related("owner", "owner__profile")
            .order_by("-star_count", "-updated_at")[:20]
        )
        context["repositories"] = repositories
        try:
            from apps.workspace.apps_app.models import DevInstallation

            context["dev_installed_set"] = set(
                DevInstallation.objects.filter(user=request.user).values_list(
                    "source_owner", "source_repo"
                )
            )
        except Exception:
            context["dev_installed_set"] = set()

    elif tab == "users":
        context["users"] = (
            User.objects.filter(is_active=True)
            .exclude(username__startswith="visitor-")
            .annotate(
                repo_count=Count("project_app_owned_projects"),
                follower_count=Count("followers"),
            )
            .select_related("profile")
            .order_by("-follower_count", "-repo_count")[:20]
        )

    elif tab == "groups":
        from apps.infra.organizations_app.models import Organization

        context["organizations"] = Organization.objects.annotate(
            member_count=Count("members")
        ).order_by("-member_count", "name")[:20]

    html = render_to_string(
        "public_projects_app/explore_content.html", context, request=request
    )
    return JsonResponse({"success": True, "html": html})


# EOF
