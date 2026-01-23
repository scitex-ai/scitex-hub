"""
Visitor Workspace Management

Handles initialization and reset of visitor project workspaces.
"""

import logging
import shutil
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import User

from apps.project_app.models import Project

logger = logging.getLogger(__name__)


class WorkspaceManager:
    """Manages visitor workspace lifecycle."""

    VISITOR_USER_PREFIX = "visitor-"

    @classmethod
    def initialize_visitor_writer_workspace(cls, project: Project, project_path: Path):
        """
        Initialize writer workspace for visitor projects (Gitea-independent).

        This is called during visitor pool initialization to ensure writer workspaces
        are created even though visitors don't have Gitea accounts.

        Args:
            project: Project model instance
            project_path: Path to project root directory
        """
        try:
            writer_dir = project_path / "scitex" / "writer"

            logger.info(f"[VisitorPool] Initializing writer workspace for {project.slug}")

            # Initialize Writer with git_strategy='none' for visitor projects
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

        # branch and tag are mutually exclusive - only pass the one that's set
        writer_kwargs = {
            "project_dir": writer_dir,
            "git_strategy": None,  # No git for visitor projects
        }
        if template_tag:
            writer_kwargs["tag"] = template_tag
        elif template_branch:
            writer_kwargs["branch"] = template_branch

        writer = Writer(**writer_kwargs)

        # Verify creation
        manuscript_dir = writer_dir / "01_manuscript"
        if manuscript_dir.exists():
            logger.info(
                f"[VisitorPool] Writer workspace initialized for {project.slug}"
            )

            # Create manuscript record (writer_initialized is a computed property)
            from apps.writer_app.models import Manuscript

            Manuscript.objects.get_or_create(
                project=project,
                defaults={
                    "owner": project.owner,
                    "title": f"{project.name} Manuscript"
                },
            )
        else:
            logger.warning(
                f"[VisitorPool] Writer workspace incomplete for {project.slug}"
            )

    @classmethod
    def reset_visitor_workspace(cls, visitor_user: User):
        """
        Reset visitor's workspace (clear content, keep structure).

        Called after visitor signs up and claims project.

        Args:
            visitor_user: Visitor user whose workspace will be reset
        """
        try:
            project_slug = "default-project"

            # Delete old project if exists
            Project.objects.filter(slug=project_slug, owner=visitor_user).delete()

            # Create fresh default project
            project = Project.objects.create(
                name="default-project",
                slug=project_slug,
                description="Try SciTeX features - sign up to save permanently!",
                owner=visitor_user,
                visibility="private",
                data_location=f"{visitor_user.username}/{project_slug}",
            )

            # Initialize directory
            cls._initialize_reset_directory(visitor_user, project, project_slug)

        except Exception as e:
            logger.error(
                f"[VisitorPool] Error resetting visitor workspace: {e}", exc_info=True
            )

    @classmethod
    def _initialize_reset_directory(cls, visitor_user: User, project: Project, project_slug: str):
        """Initialize directory for reset visitor workspace."""
        from apps.project_app.services.project_filesystem import (
            get_project_filesystem_manager,
        )

        manager = get_project_filesystem_manager(visitor_user)
        project_path = manager.base_path / project_slug

        # Ensure directory doesn't exist before copying template
        if project_path.exists():
            shutil.rmtree(project_path)
            logger.info(f"[VisitorPool] Removed existing directory before template copy")

        # Copy master template
        template_master = Path(getattr(
            settings,
            "VISITOR_TEMPLATE_PATH",
            "/app/templates/research-master"
        ))

        success = cls._copy_reset_template(template_master, project_path, manager, project)
        if success:
            # Set git_clone_path for file operations
            project.git_clone_path = str(project_path)
            project.directory_created = True
            project.save(update_fields=["git_clone_path", "directory_created"])

            logger.info(f"[VisitorPool] Reset visitor workspace: {project_slug}")

            # Initialize writer workspace for the fresh visitor project
            cls.initialize_visitor_writer_workspace(project, Path(project_path))
        else:
            logger.error(
                f"[VisitorPool] Failed to reset visitor workspace: {project_slug}"
            )

    @classmethod
    def _copy_reset_template(cls, template_master: Path, project_path: Path, manager, project: Project) -> bool:
        """Copy template during reset operation."""
        try:
            if not template_master.exists():
                logger.warning(
                    f"[VisitorPool] Master template not found at {template_master}, using basic directory"
                )
                success, project_path = manager.create_project_directory(project)
                return success
            else:
                logger.info(f"[VisitorPool] Resetting workspace from {template_master}")
                shutil.copytree(template_master, project_path, symlinks=True)
                logger.info(f"[VisitorPool] Template copied successfully for reset")
                return True

        except Exception as e:
            logger.error(f"[VisitorPool] Template copy error during reset: {e}")
            success, project_path = manager.create_project_directory(project)
            return success
