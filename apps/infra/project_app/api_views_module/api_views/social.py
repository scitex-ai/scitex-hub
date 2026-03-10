#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""API views for project social interactions (Watch, Star, Fork)."""

from __future__ import annotations

import logging

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from apps.infra.project_app.models import (
    Project,
    ProjectFork,
    ProjectStar,
    ProjectWatch,
)

from .utils import get_project_with_access

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["POST"])
def api_project_watch(request, username, slug):
    """Toggle watch status for a project."""
    try:
        project, error = get_project_with_access(request, username, slug)
        if error:
            return error

        watch, created = ProjectWatch.objects.get_or_create(
            user=request.user,
            project=project,
            defaults={"notification_settings": "all"},
        )

        if not created:
            watch.delete()
            is_watching = False
        else:
            is_watching = True

        return JsonResponse(
            {
                "success": True,
                "is_watching": is_watching,
                "watch_count": project.project_watchers.count(),
                "message": "Watching" if is_watching else "Unwatched",
            }
        )

    except Exception as e:
        logger.error(f"Error toggling watch for project {slug}: {e}")
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def api_project_star(request, username, slug):
    """Toggle star status for a project."""
    try:
        project, error = get_project_with_access(request, username, slug)
        if error:
            return error

        star, created = ProjectStar.objects.get_or_create(
            user=request.user, project=project
        )

        if not created:
            star.delete()
            is_starred = False
        else:
            is_starred = True

        return JsonResponse(
            {
                "success": True,
                "is_starred": is_starred,
                "star_count": project.project_stars_set.count(),
                "message": "Starred" if is_starred else "Unstarred",
            }
        )

    except Exception as e:
        logger.error(f"Error toggling star for project {slug}: {e}")
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def api_project_fork(request, username, slug):
    """Fork a project (create a copy under the current user's account)."""
    try:
        project, error = get_project_with_access(request, username, slug)
        if error:
            return error

        existing_fork = ProjectFork.objects.filter(
            user=request.user, original_project=project
        ).first()

        if existing_fork:
            return JsonResponse(
                {
                    "success": False,
                    "error": "You have already forked this project",
                    "forked_project_url": f"/{request.user.username}/{existing_fork.forked_project.slug}/",
                },
                status=400,
            )

        with transaction.atomic():
            fork_slug = _generate_unique_fork_slug(project, request.user)

            forked_project = Project.objects.create(
                name=f"{project.name} (fork)",
                slug=fork_slug,
                description=f"Forked from {username}/{project.name}\n\n{project.description}",
                owner=request.user,
                visibility=project.visibility,
                source_code_url=project.source_code_url,
                current_branch=project.current_branch,
            )

            ProjectFork.objects.create(
                user=request.user,
                original_project=project,
                forked_project=forked_project,
            )

            return JsonResponse(
                {
                    "success": True,
                    "message": "Project forked successfully",
                    "forked_project": {
                        "id": forked_project.id,
                        "name": forked_project.name,
                        "slug": forked_project.slug,
                        "url": f"/{request.user.username}/{forked_project.slug}/",
                    },
                    "fork_count": project.project_forks_set.count(),
                }
            )

    except Exception as e:
        logger.error(f"Error forking project {slug}: {e}")
        return JsonResponse({"success": False, "error": str(e)}, status=500)


def _generate_unique_fork_slug(project, user) -> str:
    """Generate a unique slug for a forked project."""
    base_slug = project.slug
    fork_slug = base_slug
    counter = 1
    while Project.objects.filter(slug=fork_slug, owner=user).exists():
        fork_slug = f"{base_slug}-{counter}"
        counter += 1
    return fork_slug


@login_required
@require_http_methods(["GET"])
def api_project_stats(request, username, slug):
    """Get watch/star/fork counts and user's current status."""
    try:
        project, error = get_project_with_access(request, username, slug)
        if error:
            return error

        return JsonResponse(
            {
                "success": True,
                "stats": {
                    "watch_count": project.project_watchers.count(),
                    "star_count": project.project_stars_set.count(),
                    "fork_count": project.project_forks_set.count(),
                },
                "user_status": {
                    "is_watching": ProjectWatch.objects.filter(
                        user=request.user, project=project
                    ).exists(),
                    "is_starred": ProjectStar.objects.filter(
                        user=request.user, project=project
                    ).exists(),
                    "has_forked": ProjectFork.objects.filter(
                        user=request.user, original_project=project
                    ).exists(),
                },
            }
        )

    except Exception as e:
        logger.error(f"Error getting stats for project {slug}: {e}")
        return JsonResponse({"success": False, "error": str(e)}, status=500)


# EOF
