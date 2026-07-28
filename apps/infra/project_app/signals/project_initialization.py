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

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from ..models import Project
from .project_init_helpers import _initialize_scitex_structure

logger = logging.getLogger(__name__)


def _clone_gitea_repo_to_data_dir(project):
    """
    Clone Gitea repository to Django's data directory.

    Creates a working tree at: /data/users/{username}/proj/{project_slug}/
    """
    try:
        # Get project data directory - org-owned or user-owned
        if project.is_org_owned:
            base_dir = (
                Path(settings.BASE_DIR)
                / "data"
                / "organizations"
                / project.org_owner.slug
                / "proj"
            )
        else:
            base_dir = (
                Path(settings.BASE_DIR)
                / "data"
                / "users"
                / project.owner.username
                / "proj"
            )
        base_dir.mkdir(parents=True, exist_ok=True)

        project_dir = base_dir / project.slug

        # Skip if directory already exists and is a git repo
        if project_dir.exists() and (project_dir / ".git").exists():
            logger.info(f"Project directory already exists as git repo: {project_dir}")
            return

        # Remove directory if exists but not a git repo
        if project_dir.exists():
            import shutil

            shutil.rmtree(project_dir)

        # Clone from Gitea using HTTP. The token is supplied per-op (not
        # embedded in origin); see the clone call below.
        #
        # Build the clone URL from the in-container Gitea service hostname
        # (``settings.GITEA_URL``, defaults to ``http://gitea:3000`` in
        # docker-compose deployments) rather than trusting
        # ``project.gitea_clone_url``. Gitea's API reports ``clone_url`` from
        # its own ``ROOT_URL`` config, which is set to the host-visible URL
        # (e.g. ``http://localhost:3000`` in prod, ``https://git.scitex.ai``
        # publicly). Neither of those resolves the same way from inside the
        # django container, so trusting the API value cloned to an
        # unreachable host and the broad ``except`` below swallowed the
        # subprocess failure — surfaced during operator-12834 publish demo.
        # ``settings.GITEA_URL`` is the URL Django ALREADY uses to talk to
        # Gitea (see GiteaClient), so it's the right source of truth.
        clone_url = (
            f"{settings.GITEA_URL.rstrip('/')}"
            f"/{project.owner.username}/{project.slug}.git"
        )

        # Authenticate the clone WITHOUT persisting the admin token.
        #
        # SECURITY (sec-gitea-admin-token-plaintext-in-user-gitconfig): the
        # token is handed to this single ``git`` process through the
        # ENVIRONMENT (``GIT_CONFIG_*`` -> a URL-scoped
        # ``http.<gitea>.extraHeader``), never in the clone URL and never on
        # argv. ``git clone`` therefore records the credential-less
        # ``clone_url`` as origin, so the platform admin token never lands in
        # ``.git/config`` — that file is bind-mounted read/write into the
        # user's Apptainer console at /workspace, where a token would leak
        # cross-tenant. Push/pull re-supply the token per-op the same way
        # (see git_service.build_gitea_auth_env).
        from apps.infra.project_app.services.git_service import (
            build_gitea_auth_env,
        )

        logger.info(f"Cloning Gitea repo to: {project_dir}")
        logger.info(f"  From: {clone_url}")  # credential-less URL

        result = subprocess.run(
            ["git", "clone", clone_url, str(project_dir)],
            capture_output=True,
            text=True,
            timeout=60,
            env=build_gitea_auth_env(),
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

            # Belt-and-braces: assert origin carries NO embedded credential.
            # Push/pull authenticate per-op via build_gitea_auth_env(), so the
            # token must never appear in this repo's .git/config (which is
            # bind-mounted into the user's sandbox).
            from apps.infra.project_app.services.git_service import (
                sanitize_origin_url,
            )

            sanitize_origin_url(project_dir)

            # Update project model with clone path
            project.git_clone_path = str(project_dir)
            project.directory_created = True
            project.save(update_fields=["git_clone_path", "directory_created"])

            # Setup Python virtual environment with scitex (DISABLED - use shared scitex)
            # _setup_project_venv(project, project_dir)

            # Initialize scitex structure (writer + scholar + integration)
            # Skip for app projects — they don't need writer/scholar
            if not project.is_app:
                _initialize_scitex_structure(project, project_dir)

        else:
            logger.error(f"Failed to clone repo: {result.stderr}")

    except subprocess.TimeoutExpired:
        logger.error(f"Git clone timeout for {project.slug}")
    except Exception as e:
        logger.error(f"Failed to clone Gitea repo for {project.slug}: {e}")
        logger.exception("Full traceback:")


@receiver(post_save, sender=Project)
def on_project_created_init_bibliography(sender, instance, created, **kwargs):
    """
    Ensure bibliography directory structure exists after project creation.

    This creates the basic directory structure and symlinks for bibliography
    management, but does NOT parse or merge files (that's opt-in).
    """
    # Only run for newly created projects with git clone path
    if not created or not instance.git_clone_path:
        return

    try:
        from apps.infra.project_app.services.bibliography_manager import (
            ensure_bibliography_structure,
        )

        project_path = Path(instance.git_clone_path)
        if project_path.exists():
            results = ensure_bibliography_structure(project_path)
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
