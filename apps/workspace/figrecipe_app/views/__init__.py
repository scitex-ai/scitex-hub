"""
Scientific Figure Editor - Views Package
"""

import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from apps.infra.project_app.services.project_utils import get_current_project

from ..models import JournalPreset, ScientificFigure

logger = logging.getLogger(__name__)


def figure_editor(request, figrecipe_embedded=False):
    """Main figure editor view - Vis (VisPlot-inspired)

    If visitor pool is exhausted, redirect to visitor-pool-full page.
    When figrecipe_embedded=True (from /vis-react/), the template shows
    figrecipe's iframe as the primary workspace instead of split-view.
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
                "[Vis] Browser request not authenticated - redirecting to visitor-pool-full"
            )
            return redirect("public_app:visitor_pool_full")

        # Non-browser request - return empty page
        return render(
            request,
            "figrecipe_app/editor.html",
            {
                "is_visitor": True,
                "figures": [],
                "journal_presets": JournalPreset.objects.filter(is_active=True),
                "figrecipe_embedded": figrecipe_embedded,
            },
        )

    context = {
        # is_visitor handled by context processor
        "module_name": "Vis",
        "module_icon": "fa-chart-line",
    }

    # Get user's figures
    figures = ScientificFigure.objects.filter(owner=request.user).order_by(
        "-updated_at"
    )
    context["figures"] = figures

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
            f"[Vis] User {request.user.username} viewing project: {current_project.slug}"
        )
    else:
        context["needs_project_creation"] = True

    context["journal_presets"] = JournalPreset.objects.filter(is_active=True)
    context["figrecipe_embedded"] = figrecipe_embedded

    # Ensure workspace layout renders (AI pane, Files pane, Editor pane)
    # Vis is in the registry, but /vis-react/ isn't — force for both.
    context["is_workspace_page"] = True

    return render(request, "figrecipe_app/editor.html", context)


@login_required
def figure_editor_legacy(request):
    """Legacy canvas-based figure editor (deprecated)"""
    # Get user's figures
    figures = ScientificFigure.objects.filter(owner=request.user).order_by(
        "-updated_at"
    )

    context = {
        "figures": figures,
        "journal_presets": JournalPreset.objects.filter(is_active=True),
    }

    return render(request, "figrecipe_app/legacy/editor.html", context)


@login_required
@require_http_methods(["POST"])
def create_figure(request):
    """Create a new scientific figure"""
    title = request.POST.get("title", "Untitled Figure")
    layout = request.POST.get("layout", "1x1")

    figure = ScientificFigure.objects.create(
        owner=request.user,
        title=title,
        layout=layout,
    )

    messages.success(request, f"Figure '{title}' created successfully!")
    return redirect("figrecipe_app:figure_detail", figure_id=figure.id)


@login_required
def figure_detail(request, figure_id):
    """Edit a specific figure"""
    figure = get_object_or_404(ScientificFigure, id=figure_id, owner=request.user)
    current_project = get_current_project(request, user=request.user)

    context = {
        "figure": figure,
        "figures": ScientificFigure.objects.filter(owner=request.user).order_by(
            "-updated_at"
        ),
        "journal_presets": JournalPreset.objects.filter(is_active=True),
        "current_project": current_project,
    }

    return render(request, "figrecipe_app/editor.html", context)


@login_required
def figure_list(request):
    """List all figures for user"""
    figures = ScientificFigure.objects.filter(owner=request.user).order_by(
        "-updated_at"
    )

    context = {
        "figures": figures,
    }

    return render(request, "figrecipe_app/figure_list.html", context)


def gallery_page(request):
    """
    Gallery page showing all available plot types from scitex.plt.gallery.

    Displays plot examples organized by category with thumbnails.
    Users can generate gallery into their project or view examples.
    """
    from apps.infra.project_app.services.project_utils import get_current_project

    from ..services.gallery_generator import (
        get_gallery_contents,
        list_gallery_categories,
    )

    context = {
        "module_name": "Vis Gallery",
        "module_icon": "fa-images",
    }

    # Get available categories from scitex.plt.gallery
    available = list_gallery_categories()
    context["available_categories"] = available.get("categories", {})
    context["total_available_plots"] = available.get("total_plots", 0)

    # Check if user has a project with gallery
    if request.user.is_authenticated:
        current_project = get_current_project(request, user=request.user)
        if current_project:
            context["current_project"] = current_project
            project_path = current_project.get_local_path()
            gallery_contents = get_gallery_contents(project_path)
            context["project_gallery"] = gallery_contents
            context["gallery_exists"] = gallery_contents.get("exists", False)

    return render(request, "figrecipe_app/gallery.html", context)
