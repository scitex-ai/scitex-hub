#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Marketplace page views — browse, detail, my modules."""

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


def build_marketplace_context(request, current_project=None):
    """Context builder for SPA tab switching."""
    return browse_context(request, current_project)


def browse(request):
    """Marketplace browse page — grid of module cards."""
    current_project = (
        get_current_project(request) if request.user.is_authenticated else None
    )
    context = browse_context(request, current_project)
    return render(request, "apps_app/browse.html", context)


def detail(request, module_name):
    """Module detail page — description, reviews, install button."""
    ensure_builtin_modules()
    mp_module = get_object_or_404(MarketplaceModule, module_name=module_name)
    if not can_view_module(request.user, mp_module):
        from django.http import Http404

        raise Http404
    reg_module = get_module(module_name)

    is_installed = False
    is_starred = False
    user_review = None
    if request.user.is_authenticated:
        is_installed = ModuleInstallation.objects.filter(
            user=request.user, module=mp_module
        ).exists()
        is_starred = ModuleStar.objects.filter(
            user=request.user, module=mp_module
        ).exists()
        user_review = ModuleReview.objects.filter(
            user=request.user, module=mp_module
        ).first()

    reviews = mp_module.reviews.select_related("user")[:20]
    versions = mp_module.versions.all()[:10]

    # Skill data for capabilities section
    from apps.llm_app.skills import get_skill

    skill = get_skill(module_name)

    # Submission status for owner
    pending_submission = None
    if request.user.is_authenticated and mp_module.author == request.user:
        from ..models import ModuleSubmission

        pending_submission = ModuleSubmission.objects.filter(
            module=mp_module, status="pending"
        ).first()

    return render(
        request,
        "apps_app/detail.html",
        {
            "mp_module": mp_module,
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


# EOF
