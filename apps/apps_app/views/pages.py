#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Apps page views — browse, detail, my modules."""

from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from apps.project_app.services.project_utils import get_current_project
from apps.workspace_app.registry import get_module

from ..models import (
    AppsModule,
    ModuleInstallation,
    ModuleReview,
    ModuleStar,
)
from .helpers import browse_context, can_view_module, ensure_builtin_modules


def build_apps_context(request, current_project=None):
    """Context builder for SPA tab switching."""
    return browse_context(request, current_project)


def browse(request):
    """Apps browse page — grid of module cards."""
    current_project = (
        get_current_project(request) if request.user.is_authenticated else None
    )
    context = browse_context(request, current_project)
    return render(request, "apps_app/browse.html", context)


def detail(request, module_name):
    """Module detail page — description, reviews, install button."""
    ensure_builtin_modules()
    app_module = get_object_or_404(AppsModule, module_name=module_name)
    if not can_view_module(request.user, app_module):
        from django.http import Http404

        raise Http404
    reg_module = get_module(module_name)

    is_installed = False
    is_starred = False
    user_review = None
    if request.user.is_authenticated:
        is_installed = ModuleInstallation.objects.filter(
            user=request.user, module=app_module
        ).exists()
        is_starred = ModuleStar.objects.filter(
            user=request.user, module=app_module
        ).exists()
        user_review = ModuleReview.objects.filter(
            user=request.user, module=app_module
        ).first()

    reviews = app_module.reviews.select_related("user")[:20]
    versions = app_module.versions.all()[:10]

    # Skill data for capabilities section
    from apps.llm_app.skills import get_skill

    skill = get_skill(module_name)

    # Submission status for owner
    pending_submission = None
    if request.user.is_authenticated and app_module.author == request.user:
        from ..models import ModuleSubmission

        pending_submission = ModuleSubmission.objects.filter(
            module=app_module, status="pending"
        ).first()

    return render(
        request,
        "apps_app/detail.html",
        {
            "app_module": app_module,
            "reg_module": reg_module,
            "skill": skill,
            "is_installed": is_installed,
            "is_starred": is_starred,
            "user_review": user_review,
            "reviews": reviews,
            "versions": versions,
            "pending_submission": pending_submission,
        },
    )


@login_required
def my_modules(request):
    """User's installed modules with enable/disable toggles."""
    installations = (
        ModuleInstallation.objects.filter(user=request.user)
        .select_related("module")
        .order_by("tab_order")
    )
    return render(
        request,
        "apps_app/my_modules.html",
        {"installations": installations},
    )


@login_required
def review_queue(request):
    """Staff-only review queue for pending app submissions."""
    if not request.user.is_staff:
        from django.http import Http404

        raise Http404

    from ..models import ModuleSubmission

    submissions = (
        ModuleSubmission.objects.filter(status__in=("pending", "changes_requested"))
        .select_related("module", "submitted_by", "module__project")
        .order_by("-submitted_at")
    )
    return render(
        request,
        "apps_app/review_queue.html",
        {"submissions": submissions},
    )


# EOF
