"""
Template Operations Manager Module

Handles template cloning, copying, and customization for projects.
Delegates all business logic to scitex.template.
"""

import logging
from pathlib import Path
from typing import Optional, Tuple

from ...models import Project

logger = logging.getLogger(__name__)


def _project_metadata(project: Project) -> dict:
    """Extract plain metadata dict from a Django Project model."""
    owner = project.owner
    return {
        "name": project.name,
        "description": project.description or "",
        "owner": owner.username if owner else "",
        "owner_full_name": (owner.get_full_name() if owner else "") or "",
        "id": project.id,
        "created_at": (
            project.created_at.strftime("%Y-%m-%d") if project.created_at else ""
        ),
        "updated_at": (
            project.updated_at.strftime("%Y-%m-%d %H:%M:%S")
            if project.updated_at
            else ""
        ),
        "progress": getattr(project, "progress", 0),
        "hypotheses": getattr(project, "hypotheses", "") or "",
    }


class TemplateOperationsManager:
    """Manages template creation and customization for projects."""

    def __init__(self, filesystem_manager):
        self.manager = filesystem_manager

    def create_minimal_readme(self, project: Project, project_path: Path):
        """Create minimal README file for empty projects."""
        from scitex.template import create_minimal_readme

        create_minimal_readme(str(project_path), _project_metadata(project))

    def create_project_readme(self, project: Project, project_path: Path):
        """Create comprehensive README file for the project."""
        from scitex.template import create_project_readme

        create_project_readme(str(project_path), _project_metadata(project))

    def create_project_config_files(self, project: Project, project_path: Path):
        """Create essential configuration files for the project."""
        from scitex.template import (
            create_env_template,
            create_paths_config,
            create_project_config,
        )

        meta = _project_metadata(project)
        create_project_config(str(project_path), meta)
        create_paths_config(str(project_path))
        create_env_template(str(project_path), meta)

    def create_requirements_file(self, project: Project, project_path: Path):
        """Create requirements.txt with essential scientific packages."""
        from scitex.template import create_requirements_file

        create_requirements_file(str(project_path))

    def copy_from_example_template(
        self, project_path: Path, project: Project, template_type: str = "research"
    ) -> bool:
        """Copy template structure from local or remote source."""
        try:
            if project_path.exists():
                logger.info(
                    f"Project path already exists: {project_path}, skipping template"
                )
                return False

            if not project_path.parent.exists():
                project_path.parent.mkdir(parents=True, exist_ok=True)

            from scitex.template import clone_template

            template_id = (
                "minimal" if template_type in ("minimal", "research") else template_type
            )
            git_strategy = "child" if template_type in ("minimal", "research") else None

            success = clone_template(
                template_id=template_id,
                project_dir=str(project_path),
                git_strategy=git_strategy,
            )

            if success:
                self._customize_after_clone(project_path, project, template_type)
                logger.info(
                    f"Successfully created {template_type} template at {project_path}"
                )

            return success

        except ImportError as e:
            logger.error(f"scitex package not available: {e}")
            return False
        except Exception as e:
            logger.error(f"Error creating {template_type} project template: {e}")
            return False

    def _customize_after_clone(
        self, project_path: Path, project: Project, template_type: str
    ):
        """Customize template after cloning — delegates to scitex.template."""
        from scitex.template import customize_minimal_template, customize_template

        meta = _project_metadata(project)
        if template_type == "minimal":
            customize_minimal_template(str(project_path), meta)
        else:
            customize_template(str(project_path), meta, template_type)

    def initialize_scitex_writer_template(
        self, project: Project
    ) -> Tuple[bool, Optional[Path]]:
        """Initialize SciTeX Writer template structure for a project."""
        try:
            try:
                from apps.workspace.writer_app.services import WriterService
            except ImportError:
                logger.warning("WriterService not available - writer_app not installed")
                return False, None

            writer_service = WriterService(project.id, project.owner.id)
            writer_path = writer_service.writer_dir

            if writer_path and writer_path.exists():
                logger.info(f"Writer template initialized at: {writer_path}")
                return True, writer_path

            logger.warning(
                f"Writer initialization returned path but directory doesn't exist: {writer_path}"
            )
            return False, None

        except Exception as e:
            logger.error(
                f"Error initializing SciTeX Writer template: {e}", exc_info=True
            )
            return False, None


# EOF
