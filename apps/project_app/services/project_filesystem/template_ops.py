"""
Template Operations Manager Module

Handles template cloning, copying, and customization for projects.
Delegates README and config generation to readme_config_ops.
"""

import shutil
from pathlib import Path
from typing import Optional, Tuple
import logging

from .readme_config_ops import ReadmeConfigOperationsManager
from ...models import Project

logger = logging.getLogger(__name__)


class TemplateOperationsManager:
    """Manages template creation and customization for projects."""

    def __init__(self, filesystem_manager):
        """
        Initialize TemplateOperationsManager.

        Args:
            filesystem_manager: Parent ProjectFilesystemManager instance
        """
        self.manager = filesystem_manager
        self.readme_config = ReadmeConfigOperationsManager(filesystem_manager)

    # Delegate README/Config operations
    def create_minimal_readme(self, project: Project, project_path: Path):
        """Create minimal README file for empty projects."""
        return self.readme_config.create_minimal_readme(project, project_path)

    def create_project_readme(self, project: Project, project_path: Path):
        """Create comprehensive README file for the project."""
        return self.readme_config.create_project_readme(project, project_path)

    def create_project_config_files(self, project: Project, project_path: Path):
        """Create essential configuration files for the project."""
        return self.readme_config.create_project_config_files(project, project_path)

    def create_requirements_file(self, project: Project, project_path: Path):
        """Create requirements.txt with essential scientific packages."""
        return self.readme_config.create_requirements_file(project, project_path)

    def copy_from_example_template(
        self, project_path: Path, project: Project, template_type: str = "research"
    ) -> bool:
        """
        Copy template structure from local or remote source.

        For research template: Uses local master copy
        For others: Uses git clone from GitHub

        Args:
            project_path: Path where project will be created
            project: Project instance
            template_type: Template type ('research', 'pip_project', 'singularity')

        Returns:
            True if template was copied successfully, False otherwise
        """
        try:
            if project_path.exists():
                logger.info(
                    f"Project path already exists: {project_path}, skipping template"
                )
                return False

            if not project_path.parent.exists():
                project_path.parent.mkdir(parents=True, exist_ok=True)

            if template_type == "research":
                return self._copy_research_template(project_path, project)
            else:
                return self._copy_git_template(project_path, project, template_type)

        except ImportError as e:
            logger.error(f"scitex package not available: {e}")
            logger.info("Fallback: Project will be created with basic structure")
            return False
        except Exception as e:
            logger.error(f"Error creating {template_type} project template: {e}")
            return False

    def _copy_research_template(self, project_path: Path, project: Project) -> bool:
        """Copy research template from local master or GitHub."""
        from django.conf import settings

        template_master = Path(getattr(
            settings,
            "VISITOR_TEMPLATE_PATH",
            "/app/templates/research-master"
        ))

        if not template_master.exists():
            logger.info(
                f"Master template not found at {template_master}, "
                "falling back to git clone"
            )
            from scitex.template import clone_research as clone_template
            success = clone_template(
                str(project_path),
                git_strategy=None,
                branch=None,
                tag=None
            )
        else:
            logger.info(
                f"Copying research template from {template_master} to {project_path}"
            )
            shutil.copytree(template_master, project_path, symlinks=True)
            success = True

        if success:
            self._customize_template_for_project(project_path, project, "research")
            logger.info(f"Successfully created research template at {project_path}")

        return success

    def _copy_git_template(
        self, project_path: Path, project: Project, template_type: str
    ) -> bool:
        """Clone template from GitHub."""
        if template_type == "pip_project":
            from scitex.template import clone_pip_project as clone_template
        elif template_type == "singularity":
            from scitex.template import clone_singularity as clone_template
        else:
            logger.info(f"Unknown template type: {template_type}, defaulting to research")
            from scitex.template import clone_research as clone_template

        logger.info(f"Cloning {template_type} template from GitHub to {project_path}")
        success = clone_template(
            str(project_path),
            git_strategy=None,
            branch=None,
            tag=None
        )

        if success:
            self._customize_template_for_project(project_path, project, template_type)
            logger.info(f"Successfully created {template_type} template at {project_path}")

        return success

    def _customize_template_for_project(
        self, project_path: Path, project: Project, template_type: str = "research"
    ):
        """Customize the copied template with project-specific information."""
        try:
            readme_path = project_path / "README.md"
            if readme_path.exists():
                readme_content = readme_path.read_text()
                readme_content = readme_content.replace(
                    "# SciTeX Example Research Project", f"# {project.name}"
                )
                readme_content = readme_content.replace(
                    "This is an example research project",
                    f"{project.description or 'Research project created with SciTeX Cloud'}",
                )
                readme_path.write_text(readme_content)

            paper_dir = project_path / "paper"
            if paper_dir.exists():
                title_file = paper_dir / "manuscript" / "src" / "title.tex"
                if title_file.exists():
                    title_file.write_text(f"\\title{{{project.name}}}")

                author_file = paper_dir / "manuscript" / "src" / "authors.tex"
                if author_file.exists() and project.owner:
                    author_name = (
                        project.owner.get_full_name() or project.owner.username
                    )
                    author_file.write_text(f"\\author{{{author_name}}}")

            logger.info(f"Customized template for project: {project.name}")

        except Exception as e:
            logger.error(f"Error customizing template: {e}")

    def initialize_scitex_writer_template(
        self, project: Project
    ) -> Tuple[bool, Optional[Path]]:
        """
        Initialize SciTeX Writer template structure for a project.

        Delegates to WriterService from writer_app which uses
        scitex.writer.Writer() to properly initialize the complete workspace.

        Args:
            project: Project instance

        Returns:
            Tuple of (success: bool, path: Optional[Path])
        """
        try:
            try:
                from apps.writer_app.services import WriterService
            except ImportError:
                logger.warning("WriterService not available - writer_app not installed")
                return False, None

            writer_service = WriterService(project.id, project.owner.id)
            writer = writer_service.writer
            writer_path = writer_service.writer_dir

            if writer_path and writer_path.exists():
                logger.info(f"✓ Writer template initialized at: {writer_path}")
                return True, writer_path
            else:
                logger.warning(
                    f"Writer initialization returned path but directory doesn't exist: "
                    f"{writer_path}"
                )
                return False, None

        except Exception as e:
            logger.error(f"Error initializing SciTeX Writer template: {e}", exc_info=True)
            return False, None
