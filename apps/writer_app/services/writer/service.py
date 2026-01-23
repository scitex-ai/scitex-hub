"""
Main WriterService class.

Django wrapper service for scitex.writer.Writer.
Provides convenient methods for Django views to interact with Writer instances.
Handles project directory management and caching.
"""

from pathlib import Path
from typing import Optional
from django.conf import settings
from scitex.writer import Writer
from scitex import logging
from ..git_service import GitService

# Import mixins
from .compilation import CompilationMixin
from .file_operations import FileOperationsMixin
from .templates import TemplatesMixin
from .git_operations import GitOperationsMixin
from .output import OutputMixin

logger = logging.getLogger(__name__)


class WriterService(
    CompilationMixin,
    FileOperationsMixin,
    TemplatesMixin,
    GitOperationsMixin,
    OutputMixin,
):
    """Service to manage Writer instances for Django projects."""

    def __init__(self, project_id: int, user_id: int):
        """Initialize WriterService for a specific project.

        Args:
            project_id: Django Project ID
            user_id: Django User ID
        """
        self.project_id = project_id
        self.user_id = user_id
        self._writer = None
        self._writer_dir = None
        self._git_service = None

    @property
    def writer_dir(self) -> Path:
        """Get or calculate the writer directory path (scitex/writer/)."""
        if self._writer_dir is None:
            from apps.project_app.models import Project
            from apps.project_app.services.project_filesystem import (
                get_project_filesystem_manager,
            )

            try:
                project = Project.objects.get(id=self.project_id)
                manager = get_project_filesystem_manager(project.owner)
                project_root = manager.get_project_root_path(project)

                # Check if project_root is None (directory doesn't exist)
                if project_root is None:
                    raise RuntimeError(
                        f"Project directory not found for project {self.project_id} (slug: {project.slug}). "
                        f"Please ensure the project directory exists."
                    )

                self._writer_dir = project_root / "scitex" / "writer"
            except Project.DoesNotExist:
                raise RuntimeError(f"Project {self.project_id} not found")

        return self._writer_dir

    @property
    def git_service(self) -> GitService:
        """Get or create GitService instance (lazy loading).

        Returns:
            GitService instance for this project's writer directory
        """
        if self._git_service is None:
            from django.contrib.auth.models import User

            try:
                user = User.objects.get(id=self.user_id)
                user_name = user.get_full_name() or user.username
                user_email = user.email or f"{user.username}@scitex.app"
            except User.DoesNotExist:
                user_name = "SciTeX Writer"
                user_email = "writer@scitex.app"

            self._git_service = GitService(
                writer_dir=self.writer_dir,
                user_name=user_name,
                user_email=user_email,
            )
            logger.info(
                f"WriterService: Initialized GitService for project {self.project_id} with user {user_name}"
            )

        return self._git_service

    @property
    def writer(self) -> Writer:
        """Get or create Writer instance (lazy loading).

        Returns:
            Writer instance for this project
        """
        if self._writer is None:
            from apps.project_app.models import Project

            project = Project.objects.get(id=self.project_id)
            logger.info(
                f"WriterService: Creating Writer instance for project {self.project_id} at {self.writer_dir}"
            )

            # NOTE: No need to create parent directories here!
            # scitex.template._clone_project now handles mkdir -p for parent directories.
            # This ensures Writer can create the template in any path, even if parent dirs don't exist.

            # Get template version from Django settings
            # These are read from SCITEX_WRITER_TEMPLATE_BRANCH and SCITEX_WRITER_TEMPLATE_TAG env vars
            template_branch = getattr(settings, "SCITEX_WRITER_TEMPLATE_BRANCH", None)
            template_tag = getattr(settings, "SCITEX_WRITER_TEMPLATE_TAG", None)

            # Convert "null" string to None (from environment variables)
            if template_branch == "null":
                template_branch = None
            if template_tag == "null":
                template_tag = None

            logger.info(
                f"WriterService: Using template version - branch: {template_branch}, tag: {template_tag}"
            )

            try:
                # IMPORTANT: Do NOT pass 'name' parameter to Writer
                #
                # The scitex.writer.Writer class expects to create a NEW project with its own directory.
                # When you pass a 'name' parameter, Writer creates a subdirectory: project_path/name/
                #
                # However, Django SciTeX Cloud uses an organized ecosystem structure:
                #   data/users/{username}/{project-slug}/scitex/writer/
                #
                # The 'writer' directory is already the final target where Writer should operate.
                # We pass the exact path where Writer should work, not a parent directory.
                # This prevents Writer from creating: scitex/writer/{project-name}/
                #
                # Example structure:
                #   ✓ Correct: data/users/test-user/test-002/scitex/writer/01_manuscript/
                #   ✗ Wrong:   data/users/test-user/test-002/scitex/writer/test-002/01_manuscript/
                #
                # Git Strategy: Use "parent" to share the main project's git repository
                # The writer directory is part of the main project, not a separate repo.
                #
                # Template Version: Pass branch/tag from Django settings to control which
                # version of scitex-writer template is cloned when creating new workspaces
                self._writer = Writer(
                    self.writer_dir,  # Already points to: {project-root}/scitex/writer/
                    # name=project.name,  # REMOVED - causes extra subdirectory creation
                    git_strategy="parent",  # Use parent project's git repository
                    branch=template_branch,  # Template branch from settings (e.g., "develop", "main")
                    tag=template_tag,  # Template tag from settings (e.g., "v2.0.0-rc1")
                )
                logger.info(f"WriterService: Writer instance created successfully")
            except Exception as e:
                logger.error(
                    f"WriterService: Failed to create Writer instance: {e}",
                    exc_info=True,
                )
                raise RuntimeError(f"Failed to initialize Writer: {e}") from e

        return self._writer
