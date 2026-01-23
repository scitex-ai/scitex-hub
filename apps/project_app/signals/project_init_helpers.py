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
            timeout=60
        )

        if result.returncode != 0:
            logger.error(f"Failed to create venv: {result.stderr}")
            return

        # Create requirements.txt template
        requirements_file = Path(project_dir) / "requirements.txt"
        if not requirements_file.exists():
            requirements_file.write_text("""# Project-specific dependencies
# scitex is available via --system-site-packages (shared installation)
# Add your project-specific packages here
""")

        logger.info(f"✓ Virtual environment created for {project.slug} (with system packages)")

    except subprocess.TimeoutExpired:
        logger.error(f"Timeout creating venv for {project.slug}")
    except Exception as e:
        logger.error(f"Failed to setup venv for {project.slug}: {e}")


def _initialize_writer_structure(project, project_dir):
    """
    Initialize scitex writer structure using Writer() with parent git strategy.

    Flow:
    1. Project root already has .git (from Gitea clone)
    2. Create scitex/writer/ subdirectory
    3. Writer() with git_strategy='parent' creates full structure
    4. Commit and push to Gitea

    Args:
        project: Project model instance
        project_dir: Path to project root (with .git from Gitea)
    """
    try:
        # Writer goes in scitex/writer subdirectory
        scitex_dir = project_dir / "scitex"
        writer_dir = scitex_dir / "writer"

        # Let Writer() handle structure validation - don't check manually
        # Writer() will either create new or attach to existing structure
        logger.info(f"Initializing scitex writer structure for {project.slug}")
        logger.info(f"  Project root: {project_dir}")
        logger.info(f"  Writer dir: {writer_dir}")
        logger.info(f"  Has git: {(project_dir / '.git').exists()}")

        # Initialize Writer with parent git strategy
        # This will use the project root's .git repository
        # Don't pass name parameter - let it use directory name 'writer'
        from scitex.writer import Writer

        # Get branch and tag from settings
        # In development: tag=v2.0.0-beta, branch=None
        # In production: tag=None, branch=main
        template_branch = getattr(settings, "SCITEX_WRITER_TEMPLATE_BRANCH", None)
        template_tag = getattr(settings, "SCITEX_WRITER_TEMPLATE_TAG", None)

        writer = Writer(
            project_dir=writer_dir,
            git_strategy="parent",  # Use project root's git repo
            branch=template_branch,  # Use env-specific branch (or None)
            tag=template_tag,  # Use env-specific tag (or None)
        )

        logger.success(f"✓ Scitex writer structure created for {project.slug}")
        logger.info(f"  - Manuscript: {writer.manuscript.root}")
        logger.info(f"  - Supplementary: {writer.supplementary.root}")
        logger.info(f"  - Git root: {writer.git_root}")

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
