#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Hub app index view - Central project hub."""

import logging

from django.shortcuts import redirect, render

from apps.project_app.services.project_utils import get_current_project

logger = logging.getLogger(__name__)


def index_view(request):
    """Hub main page - Central project hub with GitHub-style features.

    Layout:
    - Left sidebar: File tree (consistent with other modules)
    - Main area: Projects overview cards + Recent Activity
    - Right panel: Details/properties placeholder

    For authenticated users: loads their project + shows projects list
    For visitor users: provides demo workspace
    If visitor pool is exhausted: redirect to visitor-pool-full page
    """
    # Check if user is not authenticated (visitor allocation may have failed)
    if not request.user.is_authenticated:
        # Check if this is a browser request (has typical browser User-Agent)
        user_agent = request.META.get("HTTP_USER_AGENT", "")
        is_browser = any(
            browser in user_agent
            for browser in ["Mozilla", "Chrome", "Safari", "Firefox", "Edge", "Opera"]
        )

        if is_browser:
            # Browser request but not authenticated - visitor pool likely exhausted
            logger.info(
                "[Hub] Browser request not authenticated - redirecting to visitor-pool-full"
            )
            return redirect("public_app:visitor_pool_full")

        # Non-browser request - return empty page
        return render(
            request,
            "hub_app/index.html",
            {
                "is_visitor": True,
            },
        )

    context = {
        "is_visitor": False,
        "module_name": "Hub",
        "module_icon": "fa-home",
    }

    # Mark as demo if visitor
    if request.user.username.startswith("visitor-"):
        context["is_demo"] = True
        context["visitor_username"] = request.user.username

    # Get current project from header dropdown
    current_project = get_current_project(request, user=request.user)

    if current_project:
        context["current_project"] = current_project
        context["project"] = current_project
        logger.info(
            f"[Hub] User {request.user.username} viewing project: {current_project.slug}"
        )
    else:
        context["needs_project_creation"] = True

    # Get user's projects for overview (reusing project_app models)
    from apps.project_app.models import Project

    user_projects = Project.objects.filter(owner=request.user).order_by("-updated_at")[
        :6
    ]
    context["user_projects"] = user_projects
    context["projects_count"] = Project.objects.filter(owner=request.user).count()

    # Get recent activities (reusing social_app models)
    from apps.social_app.models import Activity

    recent_activities = Activity.objects.filter(user=request.user).order_by(
        "-created_at"
    )[:5]
    context["recent_activities"] = recent_activities

    return render(request, "hub_app/index.html", context)


# EOF
