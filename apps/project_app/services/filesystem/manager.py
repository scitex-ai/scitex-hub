"""
Project filesystem manager.

This module contains the main ProjectFilesystemManager class that coordinates
all filesystem operations for SciTeX projects.
"""

import os
import shutil
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from django.conf import settings
from django.contrib.auth.models import User
from ...models import Project
from .paths import (
    get_user_base_path,
    get_project_root_path,
    ensure_directory,
)
from .operations import (
    store_document,
    store_file,
    list_project_files,
    get_project_structure,
    delete_project_directory,
    get_storage_usage,
)
from .git_operations import clone_from_git, get_script_executions
from .templates import (
    create_workspace_info,
    create_minimal_readme,
    create_project_readme,
    create_project_config_files,
    create_requirements_file,
    customize_template_for_project,
)


class ProjectFilesystemManager:
    """Manages user-specific directory structures for SciTeX Cloud."""

    # Standardized scientific research project structure
    PROJECT_STRUCTURE = {
        "config": [],
        "data": {
            "raw": [],
            "processed": [],
            "figures": [],
            "models": [],
        },
        "scripts": [],
        "docs": ["manuscripts", "notes", "references"],
        "results": ["outputs", "reports", "analysis"],
        "temp": ["cache", "logs", "tmp"],
    }

    def __init__(self, user: User):
        self.user = user
        self.base_path = get_user_base_path(user)

    def initialize_user_workspace(self) -> bool:
        """Initialize minimal user workspace - just the base directory."""
        try:
            if not ensure_directory(self.base_path):
                return False
            create_workspace_info(self.user, self.base_path)
            return True
        except Exception as e:
            print(f"Error initializing user workspace: {e}")
            return False

    def create_project_directory(
        self,
        project: Project,
        use_template: bool = False,
        template_type: str = "research",
    ) -> Tuple[bool, Optional[Path]]:
        """Create directory structure for a new repository."""
        try:
            project_path = self.base_path / project.slug

            if not ensure_directory(self.base_path):
                return False, None

            if use_template and self._copy_from_example_template(
                project_path, project, template_type
            ):
                project.data_location = str(project_path.relative_to(self.base_path))
                project.directory_created = True
                project.save()
                return True, project_path

            if not ensure_directory(project_path):
                return False, None

            create_minimal_readme(project, project_path)

            project.data_location = str(project_path.relative_to(self.base_path))
            project.directory_created = True
            project.save()

            return True, project_path
        except Exception as e:
            print(f"Error creating project directory: {e}")
            return False, None

    def create_project_from_template(
        self, project: Project, template_type: str = "research"
    ) -> Tuple[bool, Optional[Path]]:
        """Create full template structure for an existing project."""
        import logging

        logger = logging.getLogger(__name__)

        try:
            project_path = self.get_project_root_path(project)
            if not project_path:
                error_msg = (
                    f"Project directory not found for {project.slug}. "
                    f"Expected at: {self.base_path / project.slug}."
                )
                logger.error(error_msg)
                raise RuntimeError(error_msg)

            if self._copy_from_example_template(project_path, project, template_type):
                return True, project_path

            # Fallback: Create manual structure
            for main_dir, sub_structure in self.PROJECT_STRUCTURE.items():
                main_path = project_path / main_dir
                if not ensure_directory(main_path):
                    raise RuntimeError(f"Failed to create directory: {main_path}")

                if main_dir == "scripts":
                    for subdir in ["analysis", "preprocessing", "modeling", "visualization", "utils"]:
                        if not ensure_directory(main_path / subdir):
                            raise RuntimeError(f"Failed to create directory: {main_path / subdir}")

                if isinstance(sub_structure, dict):
                    for sub_dir, sub_sub_dirs in sub_structure.items():
                        sub_path = main_path / sub_dir
                        if not ensure_directory(sub_path):
                            raise RuntimeError(f"Failed to create directory: {sub_path}")
                        for sub_sub_dir in sub_sub_dirs:
                            if not ensure_directory(sub_path / sub_sub_dir):
                                raise RuntimeError(f"Failed to create directory: {sub_path / sub_sub_dir}")
                elif isinstance(sub_structure, list):
                    for sub_dir in sub_structure:
                        if not ensure_directory(main_path / sub_dir):
                            raise RuntimeError(f"Failed to create directory: {main_path / sub_dir}")

            create_project_readme(project, project_path)
            create_project_config_files(project, project_path)
            create_requirements_file(project, project_path)

            return True, project_path
        except Exception as e:
            logger.error(f"Error creating project from template: {e}", exc_info=True)
            raise

    def get_project_root_path(self, project: Project) -> Optional[Path]:
        """Get the root directory path for a project."""
        return get_project_root_path(self.user, project)

    # Delegate to operations module
    def store_document(
        self, document, content: str, doc_type: str = "manuscripts"
    ) -> Tuple[bool, Optional[Path]]:
        """Store a document in the appropriate project directory."""
        return store_document(self.user, document, content, doc_type)

    def store_file(
        self,
        project: Project,
        file_content: bytes,
        filename: str,
        category: str = "data",
    ) -> Tuple[bool, Optional[Path]]:
        """Store a file in the project directory."""
        return store_file(self.user, project, file_content, filename, category)

    def list_project_files(
        self, project: Project, category: Optional[str] = None
    ) -> List[Dict]:
        """List files in a project directory."""
        return list_project_files(self.user, project, category)

    def get_project_structure(self, project: Project) -> Dict:
        """Get the complete directory structure for a project."""
        return get_project_structure(self.user, project)

    def delete_project_directory(self, project: Project) -> bool:
        """Delete a project directory and all its contents."""
        return delete_project_directory(self.user, project)

    def get_storage_usage(self) -> Dict:
        """Get storage usage statistics for the user."""
        return get_storage_usage(self.user)

    # Delegate to git_operations module
    def clone_from_git(
        self, project: Project, git_url: str, use_ssh: bool = True
    ) -> Tuple[bool, Optional[str]]:
        """Clone a Git repository into the project directory."""
        return clone_from_git(self.user, project, git_url, use_ssh)

    def get_script_executions(
        self, project: Project, script_name: str = None
    ) -> List[Dict]:
        """Get execution history for scripts in the project."""
        return get_script_executions(self.user, project, script_name)

    # Template operations
    def _copy_from_example_template(
        self, project_path: Path, project, template_type: str = "research"
    ) -> bool:
        """Copy template structure from local master template or clone from GitHub."""
        try:
            if project_path.exists():
                print(f"Project path already exists: {project_path}, skipping")
                return False

            if not project_path.parent.exists():
                project_path.parent.mkdir(parents=True, exist_ok=True)

            if template_type == "research":
                template_master = Path(
                    getattr(settings, "VISITOR_TEMPLATE_PATH", "/app/templates/research-master")
                )

                if not template_master.exists():
                    from scitex.template import clone_research as clone_template

                    success = clone_template(str(project_path), git_strategy=None, branch=None, tag=None)
                else:
                    shutil.copytree(template_master, project_path, symlinks=True)
                    success = True
            else:
                if template_type == "pip_project":
                    from scitex.template import clone_pip_project as clone_template
                elif template_type == "singularity":
                    from scitex.template import clone_singularity as clone_template
                else:
                    from scitex.template import clone_research as clone_template

                success = clone_template(str(project_path), git_strategy=None, branch=None, tag=None)

            if success:
                customize_template_for_project(project_path, project, template_type)

            return success

        except ImportError as e:
            print(f"scitex package not available: {e}")
            return False
        except Exception as e:
            print(f"Error creating {template_type} project template: {e}")
            return False

    def create_script_execution_tracker(
        self, project: Project, script_name: str
    ) -> Tuple[bool, Optional[Path]]:
        """Create execution tracking for a script."""
        try:
            project_path = self.get_project_root_path(project)
            if not project_path:
                return False, None

            script_base = Path(script_name).stem
            script_dir = project_path / "scripts" / script_base

            if not ensure_directory(script_dir):
                return False, None

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            execution_dir = script_dir / f"execution_{timestamp}"

            if not ensure_directory(execution_dir):
                return False, None

            running_marker = execution_dir / "RUNNING"
            with open(running_marker, "w") as f:
                f.write(f"""Script: {script_name}
Started: {datetime.now().isoformat()}
Status: Running
PID: {os.getpid()}
""")

            for output_dir in ["logs", "outputs", "figures", "data"]:
                if not ensure_directory(execution_dir / output_dir):
                    return False, None

            return True, execution_dir
        except Exception as e:
            print(f"Error creating script execution tracker: {e}")
            return False, None

    def mark_script_finished(
        self, execution_dir: Path, success: bool = True, error_msg: str = None
    ) -> bool:
        """Mark script execution as finished."""
        try:
            if not execution_dir.exists():
                return False

            running_marker = execution_dir / "RUNNING"
            if running_marker.exists():
                running_marker.unlink()

            marker = execution_dir / ("FINISHED_SUCCESS" if success else "FINISHED_ERROR")
            status = "Completed Successfully" if success else "Failed"

            with open(marker, "w") as f:
                f.write(f"""Status: {status}
Finished: {datetime.now().isoformat()}
Error: {error_msg or "None"}
""")

            summary_file = execution_dir / "execution_summary.json"
            summary = {
                "script_name": execution_dir.parent.name,
                "execution_id": execution_dir.name,
                "finished_at": datetime.now().isoformat(),
                "success": success,
                "error_message": error_msg,
                "output_files": [
                    f.name
                    for f in execution_dir.rglob("*")
                    if f.is_file() and f.name not in ["RUNNING", "FINISHED_SUCCESS", "FINISHED_ERROR"]
                ],
                "logs_available": (execution_dir / "logs").exists(),
            }

            with open(summary_file, "w") as f:
                json.dump(summary, f, indent=2)

            return True
        except Exception as e:
            print(f"Error marking script as finished: {e}")
            return False

    def initialize_scitex_writer_template(
        self, project: Project
    ) -> Tuple[bool, Optional[Path]]:
        """Initialize SciTeX Writer template structure for a project."""
        try:
            from apps.writer_app.services import WriterService
            import logging

            logger = logging.getLogger(__name__)

            writer_service = WriterService(project.id, project.owner.id)
            writer = writer_service.writer
            writer_path = writer_service.writer_dir

            if writer_path and writer_path.exists():
                logger.info(f"✓ Writer template initialized successfully at: {writer_path}")
                return True, writer_path
            else:
                logger.warning(f"Writer initialization returned path but directory doesn't exist: {writer_path}")
                return False, None

        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Error initializing SciTeX Writer template: {e}", exc_info=True)
            return False, None


def get_project_filesystem_manager(user: User) -> ProjectFilesystemManager:
    """Get or create a ProjectFilesystemManager for the user."""
    manager = ProjectFilesystemManager(user)

    if not manager.base_path.exists():
        manager.initialize_user_workspace()

    return manager


def ensure_project_directory(project: Project) -> bool:
    """Ensure a project has a directory structure."""
    manager = get_project_filesystem_manager(project.owner)

    if not manager.get_project_root_path(project):
        success, path = manager.create_project_directory(project)
        return success

    return True
