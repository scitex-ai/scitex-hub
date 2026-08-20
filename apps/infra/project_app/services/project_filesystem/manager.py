"""
Project Operations Manager Module

This module provides the main ProjectOpsManager class that integrates all
project filesystem operations including directory creation, file storage,
and execution tracking.

Extracted from project_filesystem.py for better maintainability.
"""

import logging
import os
import shutil
from pathlib import Path
from typing import Dict, Optional, Tuple

from ...models import Project
from .core import ProjectFilesystemManager
from .directory_builder import DirectoryBuilderManager
from .execution_ops import ExecutionOperationsManager
from .file_ops import FileOperationsManager
from .git_ops import GitOperationsManager
from .template_ops import TemplateOperationsManager

logger = logging.getLogger(__name__)


class WorkspaceNotAccessibleError(OSError):
    """The user's data directory exists but this process cannot traverse it.

    Distinct from "the workspace is missing", which we repair by creating it.
    This one cannot be repaired by creating anything — the directory is there
    and the operating system is refusing us. Raising a named error means the
    failure says what is wrong instead of surfacing as a bare EACCES from a
    ``Path.exists()`` call three layers down.
    """


class ProjectOpsManager(ProjectFilesystemManager):
    """Manages all project-level directory operations.

    Integrates file operations, execution tracking, and template management
    into a unified interface that extends the base ProjectFilesystemManager.
    """

    def __init__(self, user):
        """
        Initialize ProjectOpsManager.

        Args:
            user: Django User instance
        """
        super().__init__(user)
        self.file_ops = FileOperationsManager(self)
        self.execution_ops = ExecutionOperationsManager(self)
        self.template_ops = TemplateOperationsManager(self)
        self.git_ops = GitOperationsManager(self)
        self.dir_builder = DirectoryBuilderManager(self)

    def create_project_directory(
        self,
        project: Project,
        use_template: bool = False,
        template_type: str = "research",
    ) -> Tuple[bool, Optional[Path]]:
        """Create directory structure for new repository.

        Args:
            project: Project instance
            use_template: If True, create full template structure
            template_type: Template type ('research', 'pip_project', 'singularity')

        Returns:
            Tuple of (success: bool, path: Optional[Path])
        """
        try:
            base = self._get_effective_base_path(project)
            project_slug = project.slug
            project_path = base / project_slug

            if not self._ensure_directory(base):
                return False, None

            if use_template and self.template_ops.copy_from_example_template(
                project_path, project, template_type
            ):
                project.data_location = str(project_path.relative_to(base))
                project.directory_created = True
                project.save()
                return True, project_path

            if not self._ensure_directory(project_path):
                return False, None

            self.template_ops.create_minimal_readme(project, project_path)

            project.data_location = str(project_path.relative_to(base))
            project.directory_created = True
            project.save()

            return True, project_path
        except Exception as e:
            logger.error(f"Error creating project directory: {e}")
            return False, None

    def create_project_from_template(
        self, project: Project, template_type: str = "research"
    ) -> Tuple[bool, Optional[Path]]:
        """
        Create full template structure for an existing project.

        Args:
            project: Project instance
            template_type: Type of template ('research', 'pip_project', 'singularity')

        Returns:
            Tuple of (success: bool, path: Optional[Path])
        """
        try:
            project_path = self.get_project_root_path(project)
            if not project_path:
                error_msg = (
                    f"Project directory not found for {project.slug}. "
                    f"Expected at: {self.base_path / project.slug}. "
                    f"This usually means the Git repository wasn't cloned successfully. "
                    f"Please check Gitea integration and try again."
                )
                logger.error(error_msg)
                raise RuntimeError(error_msg)

            if self.template_ops.copy_from_example_template(
                project_path, project, template_type
            ):
                return True, project_path

            # Fallback: Create manual structure if scitex template fails
            self._create_fallback_structure(project_path, project, template_type)
            return True, project_path

        except Exception as e:
            logger.error(f"Error creating project from template: {e}", exc_info=True)
            raise

    def _create_fallback_structure(
        self, project_path: Path, project: Project, template_type: str
    ):
        """Create fallback directory structure if template fails."""
        self.dir_builder.build_directory_tree(project_path)
        self.template_ops.create_project_readme(project, project_path)
        self.template_ops.create_project_config_files(project, project_path)
        self.template_ops.create_requirements_file(project, project_path)

    def get_project_root_path(self, project: Project) -> Optional[Path]:
        """Get the root directory path for a project.

        For org-owned projects, uses data/organizations/{org-slug}/proj/.
        For user-owned projects, uses the user's base path.
        Always uses filesystem as source of truth.
        """
        base = self._get_effective_base_path(project)
        project_path = base / project.slug
        if project_path.exists():
            return project_path
        return None

    def _get_effective_base_path(self, project: Project) -> Path:
        """Return org base path for org-owned projects, user base path otherwise."""
        if project.is_org_owned:
            from apps.infra.project_app.services.filesystem.paths import (
                get_org_base_path,
            )

            return get_org_base_path(project.org_owner)
        return self.base_path

    def delete_project_directory(self, project: Project) -> bool:
        """Delete a project directory and all its contents."""
        try:
            project_path = self.get_project_root_path(project)
            if project_path and project_path.exists():
                shutil.rmtree(project_path)
            return True
        except Exception as e:
            logger.error(f"Error deleting project directory: {e}")
            return False

    def get_storage_usage(self) -> dict:
        """Get storage usage statistics for the user."""
        try:
            if not self.base_path.exists():
                return {"total_size": 0, "project_count": 0, "file_count": 0}

            total_size = 0
            file_count = 0

            for file_path in self.base_path.rglob("*"):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
                    file_count += 1

            project_count = len(
                [
                    p
                    for p in self.base_path.iterdir()
                    if p.is_dir() and not p.name.startswith(".")
                ]
            )

            return {
                "total_size": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "project_count": project_count,
                "file_count": file_count,
            }
        except Exception as e:
            logger.error(f"Error getting storage usage: {e}")
            return {"total_size": 0, "project_count": 0, "file_count": 0}

    # File Operations Delegation
    def store_document(self, document, content: str, doc_type: str = "manuscripts"):
        """Store a document. Delegates to file_ops."""
        return self.file_ops.store_document(document, content, doc_type)

    def store_file(
        self,
        project: Project,
        file_content: bytes,
        filename: str,
        category: str = "data",
    ):
        """Store a file. Delegates to file_ops."""
        return self.file_ops.store_file(project, file_content, filename, category)

    def list_project_files(self, project: Project, category: Optional[str] = None):
        """List project files. Delegates to file_ops."""
        return self.file_ops.list_project_files(project, category)

    def get_project_structure(self, project: Project) -> Dict:
        """Get project structure. Delegates to file_ops."""
        return self.file_ops.get_project_structure(project)

    # Execution Operations Delegation
    def create_script_execution_tracker(self, project: Project, script_name: str):
        """Create execution tracker. Delegates to execution_ops."""
        return self.execution_ops.create_script_execution_tracker(project, script_name)

    def mark_script_finished(
        self, execution_dir: Path, success: bool = True, error_msg: str = None
    ) -> bool:
        """Mark script finished. Delegates to execution_ops."""
        return self.execution_ops.mark_script_finished(
            execution_dir, success, error_msg
        )

    def get_script_executions(self, project: Project, script_name: str = None):
        """Get execution history. Delegates to execution_ops."""
        return self.execution_ops.get_script_executions(project, script_name)

    # Git Operations Delegation
    def clone_from_git(
        self, project: Project, git_url: str, use_ssh: bool = True
    ) -> Tuple[bool, Optional[str]]:
        """Clone from Git. Delegates to git_ops."""
        return self.git_ops.clone_from_git(project, git_url, use_ssh)

    # Template Operations Delegation
    def initialize_scitex_writer_template(self, project: Project):
        """Initialize Writer template. Delegates to template_ops."""
        return self.template_ops.initialize_scitex_writer_template(project)


def get_project_filesystem_manager(user):
    """
    Get or create a ProjectOpsManager for the user.

    Args:
        user: Django User instance

    Returns:
        ProjectOpsManager instance for the user
    """
    manager = ProjectOpsManager(user)

    # Path.exists() swallows ENOENT/ENOTDIR/EBADF/ELOOP but lets EACCES
    # propagate. An unguarded call here therefore turns "this process may not
    # traverse the directory" into an uncaught PermissionError three frames
    # below the view — a bare 500 with no indication of what is wrong.
    #
    # That is not hypothetical: enforce_data_dir_ownership() chowns
    # /app/data/users/<username> to uid 100000+pk and chmods it 700. When that
    # runs with enough privilege to succeed, the web process (a different uid)
    # is locked out of the very directory it must manage, and every page
    # touching the workspace 500s. Say so, with the numbers needed to fix it.
    try:
        workspace_missing = not manager.base_path.exists()
    except PermissionError as exc:
        try:
            owner_uid = manager.base_path.parent.stat().st_uid
            owner_hint = f"parent dir is owned by uid {owner_uid}"
        except OSError:
            owner_hint = "could not stat the parent directory either"
        raise WorkspaceNotAccessibleError(
            f"Cannot access the workspace for user {user.username!r} at "
            f"{manager.base_path}: {exc.strerror}. This process runs as "
            f"uid {os.getuid()} and {owner_hint}. The directory exists but is "
            f"not traversable by this process — most likely its ownership or "
            f"mode was enforced for a different uid (see "
            f"accounts_app.services.unix_user.enforce_data_dir_ownership, "
            f"which sets owner 100000+user.pk and mode 700). Fix the ownership "
            f"or the mode; creating the directory again will not help."
        ) from exc

    if workspace_missing:
        manager.initialize_user_workspace()

    return manager


def ensure_project_directory(project: Project) -> bool:
    """Ensure a project has a directory structure.

    Args:
        project: Project instance

    Returns:
        True if project has a directory, False otherwise
    """
    manager = get_project_filesystem_manager(project.owner)

    if not manager.get_project_root_path(project):
        success, path = manager.create_project_directory(project)
        return success

    return True
