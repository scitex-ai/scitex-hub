"""
Template Operations Manager Module

Handles template cloning, copying, and customization for projects.
Delegates README and config generation to readme_config_ops.
"""

import logging
from pathlib import Path
from typing import Optional, Tuple

from ...models import Project
from .readme_config_ops import ReadmeConfigOperationsManager

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

            if template_type == "minimal":
                return self._copy_minimal_template(project_path, project)
            elif template_type == "research":
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
        """Delegate to scitex.template for research template (now uses minimal)."""
        try:
            from scitex.template import clone_template

            success = clone_template(
                template_id="minimal",
                project_dir=str(project_path),
                git_strategy="child",
            )

            if success:
                self._customize_template_for_project(project_path, project, "research")
                logger.info(f"Successfully created minimal template at {project_path}")

            return success
        except ImportError:
            logger.error("scitex.template not available")
            return False

    def _copy_minimal_template(self, project_path: Path, project: Project) -> bool:
        """Delegate to scitex.template for minimal template."""
        try:
            from scitex.template import clone_template

            success = clone_template(
                template_id="minimal",
                project_dir=str(project_path),
                git_strategy="child",
            )

            if success:
                self._customize_template_for_project(project_path, project, "minimal")
                logger.info(f"Successfully created minimal template at {project_path}")

            return success
        except ImportError:
            logger.error("scitex.template not available")
            return False

    def _customize_minimal_template(self, project_path: Path, project: Project):
        """Customize minimal template with project-specific information."""
        try:
            # Update title.tex
            title_file = project_path / "scitex" / "writer" / "00_shared" / "title.tex"
            if title_file.exists():
                title_file.write_text(
                    f"%% -*- coding: utf-8 -*-\n\\title{{{project.name}}}\n\n%%%% EOF\n"
                )

            # Update authors.tex if owner has name
            if project.owner:
                author_name = project.owner.get_full_name() or project.owner.username
                author_file = (
                    project_path / "scitex" / "writer" / "00_shared" / "authors.tex"
                )
                if author_file.exists():
                    author_file.write_text(
                        f"%% -*- coding: utf-8 -*-\n"
                        f"\\author[1]{{{author_name}\\corref{{cor1}}}}\n\n"
                        f"\\address[1]{{Institution, Department, City, Country}}\n\n"
                        f"\\cortext[cor1]{{Corresponding author.}}\n\n"
                        f"%%%% EOF\n"
                    )

            logger.info(f"Customized minimal template for project: {project.name}")

        except Exception as e:
            logger.error(f"Error customizing minimal template: {e}")

    def _copy_git_template(
        self, project_path: Path, project: Project, template_type: str
    ) -> bool:
        """Clone template from GitHub using unified dispatcher."""
        from scitex.template import clone_template

        logger.info(f"Cloning {template_type} template from GitHub to {project_path}")
        success = clone_template(
            template_id=template_type,
            project_dir=str(project_path),
            git_strategy=None,
        )

        if success:
            self._customize_template_for_project(project_path, project, template_type)
            logger.info(
                f"Successfully created {template_type} template at {project_path}"
            )

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
            logger.error(
                f"Error initializing SciTeX Writer template: {e}", exc_info=True
            )
            return False, None
