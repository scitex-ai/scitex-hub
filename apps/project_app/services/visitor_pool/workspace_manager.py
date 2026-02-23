"""
Visitor Workspace Management

Handles initialization and reset of visitor project workspaces.
Uses scitex.template.clone_template() as single source of truth for templates.
"""

import logging
import shutil
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import User

from apps.project_app.models import Project

from .pool_initialization import VISITOR_TEMPLATE_ID

logger = logging.getLogger(__name__)


class WorkspaceManager:
    """Manages visitor workspace lifecycle."""

    VISITOR_USER_PREFIX = "visitor-"

    @classmethod
    def initialize_visitor_writer_workspace(cls, project: Project, project_path: Path):
        """
        Initialize writer workspace for visitor projects (Gitea-independent).

        Args:
            project: Project model instance
            project_path: Path to project root directory
        """
        try:
            writer_dir = project_path / "scitex" / "writer"

            logger.info(
                f"[VisitorPool] Initializing writer workspace for {project.slug}"
            )
            cls._create_writer_workspace(project, writer_dir)

        except Exception as e:
            logger.error(
                f"[VisitorPool] Failed to initialize writer workspace for {project.slug}: {e}"
            )
            logger.exception("Full traceback:")

    @classmethod
    def _create_writer_workspace(cls, project: Project, writer_dir: Path):
        """Create writer workspace and manuscript record."""
        from scitex.writer import Writer

        template_branch = getattr(settings, "SCITEX_WRITER_TEMPLATE_BRANCH", None)
        template_tag = getattr(settings, "SCITEX_WRITER_TEMPLATE_TAG", None)

        writer_kwargs = {
            "project_dir": writer_dir,
            "git_strategy": None,
        }
        if template_tag:
            writer_kwargs["tag"] = template_tag
        elif template_branch:
            writer_kwargs["branch"] = template_branch

        writer = Writer(**writer_kwargs)
        cls._cleanup_writer_dev_artifacts(writer_dir)

        manuscript_dir = writer_dir / "01_manuscript"
        if manuscript_dir.exists():
            logger.info(
                f"[VisitorPool] Writer workspace initialized for {project.slug}"
            )

            from apps.writer_app.models import Manuscript

            Manuscript.objects.get_or_create(
                project=project,
                defaults={
                    "owner": project.owner,
                    "title": f"{project.name} Manuscript",
                },
            )
        else:
            logger.warning(
                f"[VisitorPool] Writer workspace incomplete for {project.slug}"
            )

    @classmethod
    def _cleanup_writer_dev_artifacts(cls, writer_dir: Path):
        """Remove development artifacts from writer workspace."""
        DEV_ARTIFACTS = [
            "tests",
            "src",
            "docs",
            "examples",
            ".github",
            "pyproject.toml",
            ".readthedocs.yaml",
            "CHANGELOG.md",
            "VERSION",
            "ai",
        ]
        for name in DEV_ARTIFACTS:
            path = writer_dir / name
            if path.is_dir():
                shutil.rmtree(path)
            elif path.is_file():
                path.unlink()
            if path.exists():
                logger.info(f"[VisitorPool] Removed writer dev artifact: {name}")

    @classmethod
    def reset_visitor_workspace(cls, visitor_user: User):
        """
        Reset visitor's workspace via scitex.template (single source of truth).

        Called after visitor signs up and claims project.
        """
        try:
            project_slug = "default-project"

            Project.objects.filter(slug=project_slug, owner=visitor_user).delete()

            project = Project.objects.create(
                name="default-project",
                slug=project_slug,
                description="Try SciTeX features - sign up to save permanently!",
                owner=visitor_user,
                visibility="private",
                data_location=f"{visitor_user.username}/{project_slug}",
            )

            cls._initialize_reset_directory(visitor_user, project, project_slug)

        except Exception as e:
            logger.error(
                f"[VisitorPool] Error resetting visitor workspace: {e}", exc_info=True
            )

    @classmethod
    def _initialize_reset_directory(
        cls, visitor_user: User, project: Project, project_slug: str
    ):
        """Initialize directory for reset visitor workspace using scitex.template."""
        from scitex.template import clone_template

        from apps.project_app.services.project_filesystem import (
            get_project_filesystem_manager,
        )

        manager = get_project_filesystem_manager(visitor_user)
        project_path = manager.base_path / project_slug

        if project_path.exists():
            shutil.rmtree(project_path)
            logger.info(
                "[VisitorPool] Removed existing directory before template clone"
            )

        try:
            success = clone_template(
                VISITOR_TEMPLATE_ID,
                str(project_path),
                git_strategy=None,
            )
        except Exception as e:
            logger.error(f"[VisitorPool] Template clone error during reset: {e}")
            success = False

        if success:
            project.git_clone_path = str(project_path)
            project.directory_created = True
            project.save(update_fields=["git_clone_path", "directory_created"])

            logger.info(f"[VisitorPool] Reset visitor workspace: {project_slug}")
            cls.initialize_visitor_writer_workspace(project, Path(project_path))
        else:
            logger.error(
                f"[VisitorPool] Failed to reset visitor workspace: {project_slug}"
            )
