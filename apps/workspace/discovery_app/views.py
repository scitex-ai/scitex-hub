#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Discovery App views — public repo and user discovery workspace module."""

import logging

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Count
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.views.decorators.http import require_http_methods

from apps.infra.project_app.models import Project

logger = logging.getLogger(__name__)


def build_discovery_context(request, current_project=None):
    """Context builder for the discovery workspace module (repositories tab default)."""
    repositories = (
        Project.objects.filter(visibility="public")
        .annotate(star_count=Count("stars"))
        .select_related("owner", "owner__profile")
        .order_by("-star_count", "-updated_at")[:20]
    )

    dev_installed_set = set()
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
    }


@require_http_methods(["GET"])
def discovery_index(request):
    """GET /apps/discovery/ — Public Projects, one pane.

    This used to mount the legacy three-pane workspace shell: a left AI chat
    pane ("Ask anything about Scientific Research"), an unrelated, mostly
    empty project file pane, and the listing loaded over AJAX on the right.
    Operator 2026-09-14: one pane, in the same list/tree look as My Projects.
    The page renders the listing server-side inside the ordinary workspace
    page (module pane), so there is no second shell and no loading flash.
    Anonymous visitors keep the previous behaviour (landing page).
    """
    if not request.user.is_authenticated:
        from django.shortcuts import redirect

        return redirect("public_app:landing")

    from django.shortcuts import render

    return render(
        request, "discovery_app/index.html", build_discovery_context(request)
    )


@login_required
@require_http_methods(["GET"])
def api_explore(request):
    """GET /discovery/api/explore/?tab=repositories|users|groups — tab content."""
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
        "discovery_app/explore_content.html", context, request=request
    )
    return JsonResponse({"success": True, "html": html})


# EOF
