"""
Visitor Workspace Management

Handles initialization and reset of visitor project workspaces.
Uses scitex.template.clone_template() as single source of truth for templates.
"""

import logging
import shutil
from pathlib import Path

from django.contrib.auth.models import User

from apps.infra.project_app.models import Project

logger = logging.getLogger(__name__)


class WorkspaceManager:
    """Manages visitor workspace lifecycle."""

    VISITOR_USER_PREFIX = "visitor-"

    @classmethod
    def ensure_manuscript_record(cls, project: Project, project_path: Path):
        """
        Ensure Manuscript DB record exists for a visitor project.

        Called after scitex_minimal template clone which already creates
        scitex/writer/ with the full writer workspace.

        Args:
            project: Project model instance
            project_path: Path to project root directory
        """
        try:
            writer_dir = project_path / "scitex" / "writer"
            manuscript_dir = writer_dir / "01_manuscript"

            if manuscript_dir.exists():
                from apps.workspace.writer_app.models import Manuscript

                Manuscript.objects.get_or_create(
                    project=project,
                    defaults={
                        "owner": project.owner,
                        "title": f"{project.name} Manuscript",
                    },
                )
                logger.info(
                    f"[VisitorPool] Manuscript record ensured for {project.slug}"
                )
            else:
                logger.warning(
                    f"[VisitorPool] Writer workspace missing 01_manuscript: {writer_dir}"
                )

        except Exception as e:
            logger.error(
                f"[VisitorPool] Failed to ensure manuscript record for {project.slug}: {e}"
            )

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

        from apps.infra.project_app.services.project_filesystem import (
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
            from .pool_initialization import VISITOR_TEMPLATE_ID

            success = clone_template(
                VISITOR_TEMPLATE_ID,
                str(project_path),
                git_strategy=None,
            )
        except Exception as e:
            logger.error(f"[VisitorPool] Template clone error during reset: {e}")
            success = False

        if success:
            from .pool_initialization import PoolInitializer

            PoolInitializer._cleanup_project_dev_artifacts(project_path)

            project.git_clone_path = str(project_path)
            project.directory_created = True
            project.save(update_fields=["git_clone_path", "directory_created"])

            logger.info(f"[VisitorPool] Reset visitor workspace: {project_slug}")
            cls.ensure_manuscript_record(project, Path(project_path))
        else:
            logger.error(
                f"[VisitorPool] Failed to reset visitor workspace: {project_slug}"
            )
