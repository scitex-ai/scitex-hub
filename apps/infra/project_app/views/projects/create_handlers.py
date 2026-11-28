#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Project Creation Type Handlers

Handle different project initialization types (gitea, github, template, git, empty).

Each handler returns True on success. On failure it records the reason with
``messages.error`` and returns False; it never deletes anything itself. The
view (create.py) owns the rollback, so every failure removes the row, the
Gitea repository AND the working tree the same way (hub#1274).
"""

import logging
from pathlib import Path

from django.conf import settings
from django.contrib import messages

logger = logging.getLogger(__name__)

TEMPLATE_LABELS = {"minimal": "SciTeX Minimal", "research": "SciTeX Full"}


def _publish(request, project_dir, message, label):
    """Commit the scaffold in the new clone and push it to the project's repository.

    A scaffold that exists only on the Hub's disk is not a created project:
    the repository (what clones, the Gitea UI and backups see) would still be
    Gitea's bare README.

    A project with no clone -- Gitea unavailable, the degraded mode the
    post_save signal already allows -- has no repository to publish to.
    """
    from apps.infra.project_app.services.git_service import git_commit_and_push

    if not (Path(project_dir) / ".git").is_dir():
        logger.warning("No repository to publish the %s scaffold to", label)
        return True

    published, detail = git_commit_and_push(project_dir, message, branch="HEAD")
    if not published:
        logger.error("Publishing the %s scaffold failed: %s", label, detail)
        messages.error(
            request,
            f'The "{label}" files were created but could not be saved to the '
            "project's repository.",
        )
    return published


def handle_gitea_creation(request, project):
    """Handle Gitea-based project creation."""
    try:
        # Signal already created Gitea repo, just verify it worked
        if not project.gitea_enabled or not project.gitea_repo_id:
            # If signal failed, try manual creation
            project.create_gitea_repository()

        # Refresh from DB to get latest signal updates
        project.refresh_from_db()

        # Check if clone already succeeded (done by signal)
        project_dir = (
            Path(settings.BASE_DIR)
            / "data"
            / "users"
            / project.owner.username
            / "proj"
            / project.slug
        )

        if not project_dir.exists() or not (project_dir / ".git").exists():
            # Clone to local directory if not done by signal
            success, result = project.clone_gitea_to_local()
        else:
            # Already cloned by signal
            success = True
            result = str(project_dir)

        if success:
            messages.success(
                request,
                f'Project "{project.name}" created successfully!',
            )
            return True
        else:
            messages.error(
                request,
                f"Gitea repository created but clone failed: {result}",
            )
            logger.error(f"Clone failed for {project.slug}: {result}")
            return False

    except Exception as e:
        error_msg = str(e)
        if "already exists" in error_msg.lower() or "409" in error_msg:
            messages.error(
                request,
                f'Repository "{project.name}" already exists in Gitea. Please choose a different name.',
            )
        else:
            messages.error(request, f"Failed to create repository: {error_msg}")
        logger.error(f"Gitea creation failed for {project.slug}: {e}")
        return False


def handle_github_import(request, project, manager, git_url):
    """Handle GitHub/GitLab import."""
    if not git_url:
        messages.error(request, "Repository URL is required for importing")
        return False

    try:
        # Clone from Git repository directly (no Gitea needed)
        success, error_msg = manager.clone_from_git(project, git_url)

        if success:
            messages.success(
                request,
                f'Project "{project.name}" imported from Git repository successfully',
            )
            return True
        else:
            messages.error(request, f"Failed to clone repository: {error_msg}")
            return False

    except Exception as e:
        messages.error(request, f"Failed to import from Git: {str(e)}")
        return False


def handle_template_creation(request, project, manager, template_type):
    """Handle template-based project creation.

    The template step writes its scaffold into the fresh Gitea clone, so the
    result is published back to the repository; a project whose files exist
    only on the Hub's disk is not a created project.
    """
    label = TEMPLATE_LABELS.get(template_type, template_type)
    success, path = manager.create_project_directory(
        project, use_template=True, template_type=template_type
    )
    if not success:
        messages.error(
            request,
            f'Could not create the project from the "{label}" template.',
        )
        return False

    if template_type == "minimal":
        from apps.infra.project_app.services.first_project_samples import (
            try_seed_first_project_samples,
        )

        try_seed_first_project_samples(manager.get_project_root_path(project) or path)

    if getattr(project, "_template_scaffold_pending", False) and not _publish(
        request, path, f"Initialize {label} template", label
    ):
        return False

    messages.success(
        request,
        f'Project "{project.name}" created with the {label} template',
    )
    return True


def handle_git_clone(request, project, manager, git_url):
    """Handle Git repository cloning."""
    if not git_url:
        messages.error(request, "Repository URL is required for cloning from Git")
        return False

    # Create empty directory first
    success, path = manager.create_project_directory(project, use_template=False)
    if not success:
        messages.error(request, "Failed to create project directory")
        return False

    # Clone from Git repository
    success, error_msg = manager.clone_from_git(project, git_url)
    if success:
        messages.success(
            request,
            f'Project "{project.name}" created and cloned from Git repository',
        )
    else:
        messages.error(request, f"Project created but cloning failed: {error_msg}")
    return True


def handle_empty_creation(request, project, manager):
    """Handle empty project creation."""
    success, path = manager.create_project_directory(project, use_template=False)
    if success:
        messages.success(request, f'Project "{project.name}" created successfully')
        return True
    else:
        messages.error(request, "Failed to create project directory")
        return False


def handle_app_template_creation(request, project, manager):
    """Handle SciTeX App template creation with full boilerplate."""

    # Create project directory first
    success, path = manager.create_project_directory(project, use_template=False)
    if not success:
        messages.error(request, "Failed to create project directory")
        return False

    project_dir = Path(path) if isinstance(path, str) else path

    # Build manifest from form fields
    manifest = {
        "author": request.user.get_full_name() or request.user.username,
        "subtitle": request.POST.get("app_subtitle", "").strip(),
        "capabilities": [
            c.strip()
            for c in request.POST.get("app_capabilities", "").split(",")
            if c.strip()
        ],
        "allowed_extensions": [
            e.strip()
            for e in request.POST.get("app_filetypes", "").split(",")
            if e.strip()
        ],
        "wip": request.POST.get("app_wip") == "true",
        "ai_hint": request.POST.get("app_about", "").strip(),
    }

    # Scaffold complete app boilerplate via appmaker
    app_name = project.slug.replace("-", "_")
    if not (app_name.endswith("_app") or app_name.endswith("-app")):
        app_name = f"{app_name}_app"

    from scitex_hub.appmaker import init_app

    try:
        created = init_app(
            target_dir=str(project_dir),
            name=app_name,
            icon=request.POST.get("app_icon", "fas fa-puzzle-piece").strip(),
            description=request.POST.get("app_about", "").strip(),
            manifest=manifest,
            license_id=request.POST.get("app_license", "AGPL-3.0").strip(),
        )
        logger.info("Scaffolded %d files for app %s", len(created), app_name)
    except Exception as e:
        logger.exception("App scaffold failed for %s", app_name)
        messages.error(request, f"Could not create the app scaffold: {e}")
        return False

    if not _publish(request, project_dir, "Initialize SciTeX app scaffold", "app"):
        return False

    # Mark as app project from creation (not just at submission)
    project.is_app = True
    project.app_status = "draft"
    project.save(update_fields=["is_app", "app_status"])

    # Create scaffold repo in scitex-apps org (reverse-fork model)
    from apps.workspace.apps_app.views.api_registry import _create_app_repo

    description = request.POST.get("app_about", "").strip()
    _create_app_repo(project.slug, description=description)
    logger.info("Created scitex-apps/%s scaffold repo", project.slug)

    messages.success(
        request,
        f'App project "{project.name}" created with {len(created)} boilerplate files',
    )
    return True


def handle_scitex_initialization(request, project, manager):
    """Initialize SciTeX Writer template if requested."""
    success, writer_path = manager.initialize_scitex_writer_template(project)
    if success:
        messages.success(request, "SciTeX Writer workspace is ready")
    else:
        messages.warning(
            request,
            "Project created but SciTeX Writer template initialization failed",
        )


# EOF
