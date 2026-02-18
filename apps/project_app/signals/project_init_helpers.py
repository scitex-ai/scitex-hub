#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-29 04:54:30 (ywatanabe)"

"""
Helper utilities for project initialization.

Provides utility functions for virtual environment setup and writer structure initialization.
"""

import logging
import subprocess
from pathlib import Path

from django.conf import settings

logger = logging.getLogger(__name__)


def _setup_project_venv(project, project_dir):
    """
    Create lightweight Python virtual environment for project-specific dependencies.

    Strategy:
    - Create .venv with --system-site-packages to access shared scitex installation
    - This avoids reinstalling heavy dependencies (PyTorch, etc.) in every project
    - Users can install project-specific packages in .venv/bin/pip
    """
    try:
        venv_path = Path(project_dir) / ".venv"

        # Skip if .venv already exists
        if venv_path.exists():
            logger.info(f"Virtual environment already exists for {project.slug}")
            return

        logger.info(f"Creating virtual environment for {project.slug}")

        # Create venv with --system-site-packages to access shared scitex
        result = subprocess.run(
            ["python3", "-m", "venv", "--system-site-packages", str(venv_path)],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode != 0:
            logger.error(f"Failed to create venv: {result.stderr}")
            return

        # Create requirements.txt template
        requirements_file = Path(project_dir) / "requirements.txt"
        if not requirements_file.exists():
            requirements_file.write_text(
                """# Project-specific dependencies
# scitex is available via --system-site-packages (shared installation)
# Add your project-specific packages here
"""
            )

        logger.info(
            f"✓ Virtual environment created for {project.slug} (with system packages)"
        )

    except subprocess.TimeoutExpired:
        logger.error(f"Timeout creating venv for {project.slug}")
    except Exception as e:
        logger.error(f"Failed to setup venv for {project.slug}: {e}")


def _initialize_scitex_structure(project, project_dir):
    """
    Initialize scitex project structure (writer + scholar + integration).

    Uses scitex.template.clone_scitex_minimal() which composes:
    - scitex.writer.ensure() -> {project_dir}/scitex/writer/
    - scitex.scholar.ensure() -> {project_dir}/scitex/scholar/
    - Bibliography symlink integration

    Args:
        project: Project model instance
        project_dir: Path to project root (with .git from Gitea)
    """
    try:
        logger.info(f"Initializing scitex structure for {project.slug}")
        logger.info(f"  Project root: {project_dir}")
        logger.info(f"  Has git: {(project_dir / '.git').exists()}")

        from scitex.template import clone_scitex_minimal

        # Get branch and tag from settings
        template_branch = getattr(settings, "SCITEX_WRITER_TEMPLATE_BRANCH", None)
        template_tag = getattr(settings, "SCITEX_WRITER_TEMPLATE_TAG", None)

        success = clone_scitex_minimal(
            project_dir=str(project_dir),
            git_strategy="parent",  # Use project root's git repo
            branch=template_branch,
            tag=template_tag,
        )

        if success:
            logger.success(f"✓ Scitex structure created for {project.slug}")
        else:
            logger.error(f"clone_scitex_minimal returned False for {project.slug}")

        # Commit the new structure
        subprocess.run(["git", "add", "-A"], cwd=project_dir, capture_output=True)
        result = subprocess.run(
            ["git", "commit", "-m", "Initialize scitex writer structure"],
            cwd=project_dir,
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            logger.info("✓ Committed writer structure")

            # Push to Gitea
            result = subprocess.run(
                ["git", "push", "origin", "main"],
                cwd=project_dir,
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                logger.success(f"✓ Pushed to Gitea: {project.slug}")
            else:
                logger.warning(f"Could not push to Gitea: {result.stderr}")
        else:
            logger.info("No changes to commit (structure may already exist)")

    except Exception as e:
        logger.error(f"Failed to initialize writer structure for {project.slug}: {e}")
        logger.exception("Full traceback:")


# EOF
