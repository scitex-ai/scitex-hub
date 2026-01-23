"""
Project SciTeX Integration Methods
Contains: SciTeX-specific methods for Project model
"""

import logging
from pathlib import Path


logger = logging.getLogger(__name__)


class ProjectSciTeXMethodsMixin:
    """Mixin containing SciTeX integration methods for Project model"""

    def get_local_path(self):
        """
        Get Path object for local project directory.

        Returns:
            Path to project directory (e.g., data/users/ywatanabe/neural-decoding/)
        """
        if not self.local_path:
            # Default location
            from apps.project_app.services.project_filesystem import (
                get_project_filesystem_manager,
            )

            manager = get_project_filesystem_manager(self.owner)
            return manager.base_path / self.slug
        return Path(self.local_path)

    def has_scitex_metadata(self):
        """Check if project has scitex/.metadata/ directory."""
        local_path = self.get_local_path()
        return (local_path / "scitex" / ".metadata").exists()

    def to_scitex_project(self):
        """
        Convert Django model to SciTeXProject dataclass.

        Returns:
            SciTeXProject instance loaded from scitex/.metadata/

        Raises:
            FileNotFoundError: If scitex/.metadata/ doesn't exist
            ImportError: If scitex package is not installed
        """
        try:
            from scitex.project import SciTeXProject
        except ImportError:
            raise ImportError(
                "scitex package is not installed. Install it with: pip install scitex"
            )

        if not self.has_scitex_metadata():
            raise FileNotFoundError(
                f"Project '{self.name}' has no scitex/.metadata/ directory. "
                f"Call initialize_scitex_metadata() first."
            )

        return SciTeXProject.load_from_directory(self.get_local_path())

    def initialize_scitex_metadata(self):
        """
        Initialize scitex/.metadata/ directory for existing Django project.

        This is used during migration to add scitex/.metadata/ to projects that don't have it yet.

        Returns:
            Newly created SciTeXProject

        Raises:
            FileExistsError: If scitex/.metadata/ already exists
            ImportError: If scitex package is not installed
        """
        try:
            from scitex.project import SciTeXProject
        except ImportError:
            raise ImportError(
                "scitex package is not installed. Install it with: pip install scitex"
            )

        if self.has_scitex_metadata():
            raise FileExistsError(
                f"Project '{self.name}' already has scitex/.metadata/"
            )

        local_path = self.get_local_path()

        # Create directory if it doesn't exist
        local_path.mkdir(parents=True, exist_ok=True)

        # Create SciTeXProject
        scitex_project = SciTeXProject.create(
            name=self.name,
            path=local_path,
            owner=self.owner.username,
            description=self.description,
            visibility=self.visibility,
            template=None,  # Unknown for existing projects
            tags=[],  # No tags in current Django model
            init_git=False,  # Git might already be initialized
        )

        # Link Django project to SciTeXProject
        self.scitex_project_id = scitex_project.project_id
        self.local_path = str(local_path)
        self.save(update_fields=["scitex_project_id", "local_path"])

        logger.info(
            f"Initialized scitex metadata for project '{self.name}' "
            f"(ID: {scitex_project.project_id})"
        )

        return scitex_project

    def sync_from_scitex(self):
        """
        Update Django model from SciTeXProject metadata.

        Use this when scitex/.metadata/ is the source of truth (e.g., after local edits).
        """
        scitex_project = self.to_scitex_project()

        # Update fields from SciTeXProject
        self.name = scitex_project.name
        self.slug = scitex_project.slug
        self.description = scitex_project.description
        self.visibility = scitex_project.visibility
        self.storage_used = scitex_project.storage_used

        self.save()

        logger.info(f"Synced Django project '{self.name}' from scitex metadata")

    def sync_to_scitex(self):
        """
        Update SciTeXProject from Django model.

        Use this when Django model is the source of truth (e.g., after web UI changes).
        """
        scitex_project = self.to_scitex_project()

        # Update SciTeXProject fields
        scitex_project.name = self.name
        scitex_project.slug = self.slug
        scitex_project.description = self.description
        scitex_project.visibility = self.visibility

        # Save to scitex/.metadata/
        scitex_project.save()

        logger.info(f"Synced scitex metadata from Django project '{self.name}'")

    def update_storage_from_scitex(self):
        """
        Calculate storage using SciTeXProject and update Django model.

        Returns:
            Storage size in bytes
        """
        if not self.has_scitex_metadata():
            # Fall back to old method
            return self.update_storage_usage()

        scitex_project = self.to_scitex_project()
        storage = scitex_project.update_storage_usage()

        # Update Django model
        self.storage_used = storage
        self.save(update_fields=["storage_used"])

        return storage
