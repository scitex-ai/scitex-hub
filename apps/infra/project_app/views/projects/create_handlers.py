#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Project Creation Type Handlers

Handle different project initialization types (gitea, github, template, git, empty).
"""

import logging
from pathlib import Path

from django.conf import settings
from django.contrib import messages

logger = logging.getLogger(__name__)


def handle_gitea_creation(request, project):
    """Handle Gitea-based project creation."""
    try:
        # Signal already created Gitea repo, just verify it worked
        if not project.gitea_enabled or not project.gitea_repo_id:
            # If signal failed, try manual creation
            repo = project.create_gitea_repository()

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
            project.delete()
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
        project.delete()
        return False


def handle_github_import(request, project, manager, git_url):
    """Handle GitHub/GitLab import."""
    if not git_url:
        messages.error(request, "Repository URL is required for importing")
        project.delete()
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
            project.delete()
            return False

    except Exception as e:
        messages.error(request, f"Failed to import from Git: {str(e)}")
        project.delete()
        return False


def handle_template_creation(request, project, manager, template_type):
    """Handle template-based project creation."""
    success, path = manager.create_project_directory(
        project, use_template=True, template_type=template_type
    )
    if success:
        messages.success(
            request,
            f'Project "{project.name}" created with {template_type} template',
        )
        return True
    else:
        messages.error(request, "Failed to create project with template")
        project.delete()
        return False


def handle_git_clone(request, project, manager, git_url):
    """Handle Git repository cloning."""
    if not git_url:
        messages.error(request, "Repository URL is required for cloning from Git")
        project.delete()
        return False

    # Create empty directory first
    success, path = manager.create_project_directory(project, use_template=False)
    if not success:
        messages.error(request, "Failed to create project directory")
        project.delete()
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
        project.delete()
        return False


def handle_app_template_creation(request, project, manager):
    """Handle SciTeX App template creation with full boilerplate."""
    from scitex_cloud.appmaker import scaffold

    # Create project directory first
    success, path = manager.create_project_directory(project, use_template=False)
    if not success:
        messages.error(request, "Failed to create project directory")
        project.delete()
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

    try:
        created = scaffold(
            target_dir=str(project_dir),
            name=app_name,
            icon=request.POST.get("app_icon", "fas fa-puzzle-piece").strip(),
            description=request.POST.get("app_about", "").strip(),
            manifest=manifest,
            license_id=request.POST.get("app_license", "AGPL-3.0").strip(),
        )
        logger.info("Scaffolded %d files for app %s", len(created), app_name)
    except Exception as e:
        logger.error("App scaffold failed for %s: %s", app_name, e)
        messages.warning(
            request,
            f"Project created but scaffold incomplete: {e}",
        )
        return True

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
        messages.success(
            request, "SciTeX Writer template initialized at scitex/writer/"
        )
    else:
        messages.warning(
            request,
            "Project created but SciTeX Writer template initialization failed",
        )


# EOF
