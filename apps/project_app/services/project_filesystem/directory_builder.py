"""
Directory Builder Module

Thin wrapper delegating to scitex.template directory structure.
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class DirectoryBuilderManager:
    """Manages project directory structure creation."""

    def __init__(self, filesystem_manager):
        self.manager = filesystem_manager

    def build_directory_tree(self, project_path: Path):
        """Build standardized project directory tree structure."""
        from scitex.template import build_directory_tree

        build_directory_tree(str(project_path))


# EOF
