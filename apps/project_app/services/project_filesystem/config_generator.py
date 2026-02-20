"""
Configuration File Generator Module

Thin wrapper delegating to scitex.template config generation.
"""

import logging
from pathlib import Path

from ...models import Project
from .template_ops import _project_metadata

logger = logging.getLogger(__name__)


class ConfigGeneratorManager:
    """Manages project configuration file creation."""

    def __init__(self, filesystem_manager):
        self.manager = filesystem_manager

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


# EOF
