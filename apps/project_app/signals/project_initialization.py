#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-29 04:54:30 (ywatanabe)"

"""
Signals for project initialization.

Handles cloning of Gitea repositories and bibliography structure setup.
"""

import logging
import subprocess
from pathlib import Path
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from ..models import Project
from .project_init_helpers import _initialize_writer_structure

logger = logging.getLogger(__name__)


def _clone_gitea_repo_to_data_dir(project):
    """
    Clone Gitea repository to Django's data directory.

    Creates a working tree at: /data/users/{username}/proj/{project_slug}/
    """
    try:
        # Get user data directory - must match ProjectFilesystemManager structure
        user_data_dir = (
            Path(settings.BASE_DIR) / "data" / "users" / project.owner.username / "proj"
        )
        user_data_dir.mkdir(parents=True, exist_ok=True)

        project_dir = user_data_dir / project.slug

        # Skip if directory already exists and is a git repo
        if project_dir.exists() and (project_dir / ".git").exists():
            logger.info(f"Project directory already exists as git repo: {project_dir}")
            return

        # Remove directory if exists but not a git repo
        if project_dir.exists():
            import shutil
            shutil.rmtree(project_dir)

        # Clone from Gitea using HTTP with embedded token for authentication
        # Format: http://{token}@gitea:3000/{owner}/{repo}.git
        clone_url = project.gitea_clone_url

        # Inject Gitea admin token into URL for authentication
        # Clone URL format from Gitea: http://gitea:3000/owner/repo.git
        # Authenticated format needed: http://{token}@gitea:3000/owner/repo.git
        gitea_token = settings.GITEA_TOKEN

        if gitea_token and clone_url:
            # Parse and inject token: http://gitea:3000/... → http://{token}@gitea:3000/...
            if "://" in clone_url:
                protocol, rest = clone_url.split("://", 1)
                authenticated_clone_url = f"{protocol}://{gitea_token}@{rest}"
            else:
                authenticated_clone_url = clone_url
        else:
            authenticated_clone_url = clone_url

        logger.info(f"Cloning Gitea repo to: {project_dir}")
        logger.info(f"  From: {clone_url}")  # Log original URL (without token)

        result = subprocess.run(
            ["git", "clone", authenticated_clone_url, str(project_dir)],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode == 0:
            logger.info(f"✓ Gitea repo cloned to: {project_dir}")

            # Set git config for this repo
            subprocess.run(
                [
                    "git",
                    "config",
                    "user.name",
                    project.owner.get_full_name() or project.owner.username,
                ],
                cwd=project_dir,
                capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.email", project.owner.email],
                cwd=project_dir,
                capture_output=True,
            )

            # Configure git credentials for push (embed token in URL)
            from apps.project_app.services.git_service import (
                configure_git_credentials,
            )

            configure_git_credentials(
                project_dir=project_dir,
                username=project.owner.username,
                token=settings.GITEA_TOKEN,
            )

            # Update project model with clone path
            project.git_clone_path = str(project_dir)
            project.directory_created = True
            project.save(update_fields=["git_clone_path", "directory_created"])

            # Setup Python virtual environment with scitex (DISABLED - use shared scitex)
            # _setup_project_venv(project, project_dir)

            # Initialize scitex writer structure in scitex/writer subdirectory
            _initialize_writer_structure(project, project_dir)

        else:
            logger.error(f"Failed to clone repo: {result.stderr}")

    except subprocess.TimeoutExpired:
        logger.error(f"Git clone timeout for {project.slug}")
    except Exception as e:
        logger.error(f"Failed to clone Gitea repo for {project.slug}: {e}")
        logger.exception("Full traceback:")


@receiver(post_save, sender=Project)
def ensure_bibliography_structure(sender, instance, created, **kwargs):
    """
    Ensure bibliography directory structure exists after project creation.

    This creates the basic directory structure and symlinks for bibliography
    management, but does NOT parse or merge files (that's opt-in).
    """
    # Only run for newly created projects with git clone path
    if not created or not instance.git_clone_path:
        return

    try:
        from apps.project_app.services.bibliography_manager import (
            ensure_bibliography_structure as ensure_structure,
        )

        project_path = Path(instance.git_clone_path)
        if project_path.exists():
            results = ensure_structure(project_path)
            if results["success"]:
                logger.info(f"✓ Bibliography structure initialized for {instance.slug}")
            else:
                logger.warning(
                    f"Bibliography structure initialization had errors: {results['errors']}"
                )

    except Exception as e:
        # Non-critical error, log and continue
        logger.warning(
            f"Failed to initialize bibliography structure for {instance.slug}: {e}"
        )


# EOF
