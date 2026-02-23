"""
Visitor Pool Initialization

Handles creation of visitor accounts, default projects, and directory setup.
Uses scitex.template.clone_template() as single source of truth for templates.
"""

import logging
import shutil
from pathlib import Path

from django.contrib.auth.models import User

from apps.project_app.models import Project

logger = logging.getLogger(__name__)

VISITOR_TEMPLATE_ID = "research_minimal"


class PoolInitializer:
    """Initializes visitor pool with accounts and projects."""

    VISITOR_USER_PREFIX = "visitor-"
    DEFAULT_PROJECT_PREFIX = "default-project-"

    @classmethod
    def initialize_pool(cls, pool_size: int) -> int:
        """
        Create visitor pool (visitor-001 to visitor-N by default).

        Args:
            pool_size: Number of visitor accounts to create

        Returns:
            int: Number of visitor accounts created
        """
        if cls._check_pool_ready(pool_size):
            logger.info(
                f"[VisitorPool] Pool already initialized: {pool_size}/{pool_size} ready"
            )
            from .gitea_integration import GiteaIntegration

            GiteaIntegration.ensure_gitea_users_exist(pool_size)
            return 0

        created_count = 0

        for i in range(1, pool_size + 1):
            visitor_num = f"{i:03d}"
            username = f"{cls.VISITOR_USER_PREFIX}{visitor_num}"
            project_slug = "default-project"

            user, user_created = cls._create_visitor_user(username)
            if user_created:
                logger.info(f"[VisitorPool] Created user: {username}")

            from .gitea_integration import GiteaIntegration

            GiteaIntegration.ensure_user_in_gitea(username, visitor_num)

            project, project_created = cls._create_default_project(user, project_slug)

            success = cls._initialize_project_directory(user, project, project_slug)
            if success:
                created_count += 1
            elif project_created:
                project.delete()

        if created_count > 0:
            logger.info(
                f"[VisitorPool] Pool initialization complete: {created_count} new projects"
            )
        else:
            logger.info(f"[VisitorPool] Pool already initialized: {pool_size} ready")

        return created_count

    @classmethod
    def _check_pool_ready(cls, pool_size: int) -> bool:
        """Check if pool is already fully initialized."""
        for i in range(1, pool_size + 1):
            username = f"{cls.VISITOR_USER_PREFIX}{i:03d}"
            project_slug = "default-project"

            try:
                user = User.objects.get(username=username)
                project = Project.objects.get(slug=project_slug, owner=user)

                from apps.project_app.services.project_filesystem import (
                    get_project_filesystem_manager,
                )

                manager = get_project_filesystem_manager(user)
                project_root = manager.get_project_root_path(project)

                if not (project_root and project_root.exists()):
                    return False
            except (User.DoesNotExist, Project.DoesNotExist):
                return False

        return True

    @classmethod
    def _create_visitor_user(cls, username: str) -> tuple:
        """Create visitor user if doesn't exist."""
        user, user_created = User.objects.get_or_create(
            username=username,
            defaults={
                "email": f"{username}@visitor.scitex.local",
                "is_active": True,
            },
        )
        if user_created:
            user.set_unusable_password()
            user.save()
        return user, user_created

    @classmethod
    def _create_default_project(cls, user: User, project_slug: str) -> tuple:
        """Create default project if doesn't exist."""
        project, project_created = Project.objects.get_or_create(
            slug=project_slug,
            owner=user,
            defaults={
                "name": "default-project",
                "description": "Try SciTeX features - sign up to save permanently!",
                "visibility": "private",
                "data_location": f"{user.username}/{project_slug}",
            },
        )
        return project, project_created

    @classmethod
    def _initialize_project_directory(
        cls, user: User, project: Project, project_slug: str
    ) -> bool:
        """Initialize project directory via scitex.template.clone_template()."""
        from apps.project_app.services.project_filesystem import (
            get_project_filesystem_manager,
        )

        from .workspace_manager import WorkspaceManager

        manager = get_project_filesystem_manager(user)
        project_root = manager.get_project_root_path(project)

        if not (project_root and project_root.exists()):
            project_path = manager.base_path / project_slug

            if project_path.exists():
                shutil.rmtree(project_path)

            success = cls._clone_template(project_path)
            if not success:
                return False

            cls._cleanup_project_dev_artifacts(project_path)

            project.git_clone_path = str(project_path)
            project.directory_created = True
            project.save(update_fields=["git_clone_path", "directory_created"])

            logger.info(
                f"[VisitorPool] Created project: {project_slug} at {project_path}"
            )
            WorkspaceManager.initialize_visitor_writer_workspace(
                project, Path(project_path)
            )
        else:
            logger.info(
                f"[VisitorPool] Project directory already exists: {project_root}"
            )
            if not project.git_clone_path:
                project.git_clone_path = str(project_root)
                project.save(update_fields=["git_clone_path"])

            WorkspaceManager.initialize_visitor_writer_workspace(project, project_root)

        return True

    @classmethod
    def reset_all_project_directories(cls, pool_size: int) -> int:
        """
        Reset all visitor project directories to default template state.

        Uses scitex.template.clone_template() for consistent template content.

        Returns:
            int: Number of directories reset
        """
        reset_count = 0

        for i in range(1, pool_size + 1):
            username = f"{cls.VISITOR_USER_PREFIX}{i:03d}"
            project_slug = "default-project"

            try:
                user = User.objects.get(username=username)
                project = Project.objects.get(slug=project_slug, owner=user)

                from apps.project_app.services.project_filesystem import (
                    get_project_filesystem_manager,
                )

                manager = get_project_filesystem_manager(user)
                project_path = manager.base_path / project_slug

                # Remove existing directory if present
                if project_path.exists():
                    shutil.rmtree(project_path)
                    logger.info(f"[VisitorPool] Removed directory for {username}")

                # Clone template via scitex.template (single source of truth)
                success = cls._clone_template(project_path)
                if success:
                    cls._cleanup_project_dev_artifacts(project_path)
                    reset_count += 1

                    project.git_clone_path = str(project_path)
                    project.directory_created = True
                    project.save(update_fields=["git_clone_path", "directory_created"])

                    logger.info(f"[VisitorPool] Reset directory for {username}")

                    from .workspace_manager import WorkspaceManager

                    WorkspaceManager.initialize_visitor_writer_workspace(
                        project, project_path
                    )
                else:
                    logger.error(
                        f"[VisitorPool] Failed to reset directory for {username}"
                    )

            except (User.DoesNotExist, Project.DoesNotExist) as e:
                logger.warning(f"[VisitorPool] Skipping reset for {username}: {e}")
            except Exception as e:
                logger.error(f"[VisitorPool] Error resetting {username}: {e}")

        logger.info(f"[VisitorPool] Reset {reset_count} project directories")
        return reset_count

    @classmethod
    def _cleanup_project_dev_artifacts(cls, project_path: Path):
        """Remove development artifacts from project template."""
        DEV_ARTIFACTS = [
            ".github",
            ".readthedocs.yaml",
            "scripts/containers",
        ]
        for name in DEV_ARTIFACTS:
            path = project_path / name
            if path.is_dir():
                shutil.rmtree(path)
            elif path.is_file():
                path.unlink()

    @classmethod
    def _clone_template(cls, project_path: Path) -> bool:
        """Clone template via scitex.template.clone_template() (single source of truth)."""
        from scitex.template import clone_template

        try:
            logger.info(
                f"[VisitorPool] Cloning '{VISITOR_TEMPLATE_ID}' to {project_path}"
            )
            success = clone_template(
                VISITOR_TEMPLATE_ID,
                str(project_path),
                git_strategy=None,
            )
            if success:
                logger.info("[VisitorPool] Template cloned successfully")
            else:
                logger.error("[VisitorPool] Template clone returned False")
            return success

        except Exception as e:
            logger.error(f"[VisitorPool] Template clone error: {e}")
            return False
