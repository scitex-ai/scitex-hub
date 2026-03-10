"""
README File Generator Module

Thin wrapper delegating to scitex.template README and config generation.
"""

import logging
from pathlib import Path

from ...models import Project
from .config_generator import ConfigGeneratorManager
from .template_ops import _project_metadata

logger = logging.getLogger(__name__)


class ReadmeConfigOperationsManager:
    """Manages README and configuration file creation for projects."""

    def __init__(self, filesystem_manager):
        self.manager = filesystem_manager
        self.config_gen = ConfigGeneratorManager(filesystem_manager)

    def create_project_config_files(self, project: Project, project_path: Path):
        """Create essential configuration files for the project."""
        return self.config_gen.create_project_config_files(project, project_path)

    def create_requirements_file(self, project: Project, project_path: Path):
        """Create requirements.txt with essential scientific packages."""
        return self.config_gen.create_requirements_file(project, project_path)

    def create_minimal_readme(self, project: Project, project_path: Path):
        """Create minimal README file for empty projects."""
        from scitex.template import create_minimal_readme

        create_minimal_readme(str(project_path), _project_metadata(project))

    def create_project_readme(self, project: Project, project_path: Path):
        """Create comprehensive README file for the project."""
        from scitex.template import create_project_readme

        create_project_readme(str(project_path), _project_metadata(project))


# EOF
