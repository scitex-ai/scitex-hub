#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""App Submission API — validate, submit, and check status for marketplace apps."""

from __future__ import annotations

import json
import logging

from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from apps.apps_app.models import (
    CATEGORY_CHOICES,
    MarketplaceModule,
    ModuleSubmission,
)
from apps.project_app.models import Project
from apps.project_app.services.app_validator import validate_app
from apps.project_app.services.license_generator import generate_license_file

from .permissions import check_project_write_access

logger = logging.getLogger(__name__)

VALID_CATEGORIES = {c[0] for c in CATEGORY_CHOICES}
VALID_LICENSES = {"AGPL-3.0", "MIT", "Apache-2.0", "BSD-3-Clause"}
VALID_VISIBILITIES = {"private", "unlisted", "public"}


def _get_project_or_404(username, slug):
    """Resolve project from URL kwargs."""
    try:
        return Project.objects.get(owner__username=username, slug=slug)
    except Project.DoesNotExist:
        return None


@require_POST
def api_app_validate(request, username, slug):
    """Run app validation against the project's Gitea repo.

    POST /api/projects/<username>/<slug>/app/validate/
    Returns: {success, errors: [...]}
    """
    project = _get_project_or_404(username, slug)
    if project is None:
        return JsonResponse(
            {"success": False, "error": "Project not found"}, status=404
        )

    if not check_project_write_access(request, project):
        return JsonResponse(
            {"success": False, "error": "Permission denied"}, status=403
        )

    errors = validate_app(project)
    return JsonResponse(
        {
            "success": len(errors) == 0,
            "errors": errors,
        }
    )


@require_POST
def api_app_submit(request, username, slug):
    """Submit project to the marketplace.

    POST /api/projects/<username>/<slug>/app/submit/
    Body (JSON): {license, category, short_description}
    """
    project = _get_project_or_404(username, slug)
    if project is None:
        return JsonResponse(
            {"success": False, "error": "Project not found"}, status=404
        )

    if not check_project_write_access(request, project):
        return JsonResponse(
            {"success": False, "error": "Permission denied"}, status=403
        )

    if project.app_status in ("submitted", "under_review"):
        return JsonResponse(
            {"success": False, "error": "Project is already under review"},
            status=400,
        )

    # Parse body
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        body = {}

    spdx_license = body.get("license", "AGPL-3.0")
    category = body.get("category", "")
    visibility = body.get("visibility", "private")
    short_description = body.get("short_description", project.description[:200])

    if spdx_license not in VALID_LICENSES:
        return JsonResponse(
            {"success": False, "error": f"Invalid license: {spdx_license}"},
            status=400,
        )
    if category and category not in VALID_CATEGORIES:
        return JsonResponse(
            {"success": False, "error": f"Invalid category: {category}"},
            status=400,
        )
    if visibility not in VALID_VISIBILITIES:
        return JsonResponse(
            {"success": False, "error": f"Invalid visibility: {visibility}"},
            status=400,
        )

    # Run validation
    errors = validate_app(project)

    # If LICENSE is missing, try to auto-generate it
    license_missing = any("Missing required file: LICENSE" in e for e in errors)
    if license_missing:
        if generate_license_file(project, spdx_license):
            # Re-validate after generating LICENSE
            errors = validate_app(project)

    if errors:
        return JsonResponse({"success": False, "errors": errors}, status=400)

    # Update project fields
    now = timezone.now()
    project.is_app = True
    project.app_status = "submitted"
    project.app_license = spdx_license
    project.app_category = category
    project.app_submitted_at = now
    project.save(
        update_fields=[
            "is_app",
            "app_status",
            "app_license",
            "app_category",
            "app_submitted_at",
        ]
    )

    # Create or update MarketplaceModule
    module_name = f"user_{project.owner.username}_{project.slug}".replace("-", "_")
    mp_module, _created = MarketplaceModule.objects.get_or_create(
        module_name=module_name,
        defaults={
            "author": project.owner,
            "short_description": short_description,
            "category": category or "other",
            "repository_url": project.gitea_repo_url or "",
            "project": project,
            "visibility": visibility,
        },
    )
    if not _created:
        mp_module.short_description = short_description
        mp_module.category = category or mp_module.category
        mp_module.project = project
        mp_module.visibility = visibility
        mp_module.save(
            update_fields=["short_description", "category", "project", "visibility"]
        )

    # Create submission record
    ModuleSubmission.objects.create(
        module=mp_module,
        submitted_by=request.user,
        status="pending",
    )

    # Send confirmation email to author
    try:
        from apps.project_app.services.email_service import EmailService

        EmailService.send_app_submission_received(request.user, module_name)
    except Exception:
        logger.warning(
            "Failed to send submission confirmation email for %s", module_name
        )

    return JsonResponse(
        {
            "success": True,
            "app_status": project.app_status,
            "module_name": module_name,
        }
    )


@require_GET
def api_app_status(request, username, slug):
    """Get current app submission status.

    GET /api/projects/<username>/<slug>/app/status/
    """
    project = _get_project_or_404(username, slug)
    if project is None:
        return JsonResponse(
            {"success": False, "error": "Project not found"}, status=404
        )

    data = {
        "success": True,
        "is_app": project.is_app,
        "app_status": project.app_status,
        "app_license": project.app_license,
        "app_category": project.app_category,
        "app_submitted_at": (
            project.app_submitted_at.isoformat() if project.app_submitted_at else None
        ),
        "app_reviewed_at": (
            project.app_reviewed_at.isoformat() if project.app_reviewed_at else None
        ),
    }
    return JsonResponse(data)


@require_POST
def api_app_scaffold(request, username, slug):
    """Scaffold app template files in a project's Gitea repo.

    POST /api/projects/<username>/<slug>/app/scaffold/
    """
    project = _get_project_or_404(username, slug)
    if project is None:
        return JsonResponse(
            {"success": False, "error": "Project not found"}, status=404
        )

    if not check_project_write_access(request, project):
        return JsonResponse(
            {"success": False, "error": "Permission denied"}, status=403
        )

    try:
        from apps.project_app.services.app_template import create_app_from_template

        created = create_app_from_template(project)
        return JsonResponse(
            {
                "success": True,
                "created_files": created,
                "message": f"Scaffolded {len(created)} files.",
            }
        )
    except Exception as e:
        logger.exception("App scaffold failed for %s/%s", username, slug)
        return JsonResponse(
            {"success": False, "error": f"Scaffold failed: {e}"}, status=500
        )


# EOF
