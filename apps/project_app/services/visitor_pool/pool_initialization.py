"""
Visitor Pool Initialization

Handles creation of visitor accounts, default projects, and directory setup.
"""

import logging
import os
import secrets
import shutil
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import User

from apps.project_app.models import Project

logger = logging.getLogger(__name__)


class PoolInitializer:
    """Initializes visitor pool with accounts and projects."""

    VISITOR_USER_PREFIX = "visitor-"
    DEFAULT_PROJECT_PREFIX = "default-project-"

    @classmethod
    def initialize_pool(cls, pool_size: int) -> int:
        """
        Create visitor pool (visitor-001 to visitor-N by default).

        Run once during deployment: python manage.py create_visitor_pool

        Args:
            pool_size: Number of visitor accounts to create

        Returns:
            int: Number of visitor accounts created
        """
        # Fast-path: Check if pool is already fully initialized
        if cls._check_pool_ready(pool_size):
            logger.info(
                f"[VisitorPool] Pool already initialized: {pool_size}/{pool_size} visitor accounts ready"
            )
            # Still ensure Gitea users exist (idempotent)
            from .gitea_integration import GiteaIntegration
            GiteaIntegration.ensure_gitea_users_exist(pool_size)
            return 0

        created_count = 0

        for i in range(1, pool_size + 1):
            visitor_num = f"{i:03d}"
            username = f"{cls.VISITOR_USER_PREFIX}{visitor_num}"
            project_slug = "default-project"

            # Create visitor user
            user, user_created = cls._create_visitor_user(username)
            if user_created:
                logger.info(f"[VisitorPool] Created user: {username}")

            # Ensure user exists in Gitea
            from .gitea_integration import GiteaIntegration
            GiteaIntegration.ensure_user_in_gitea(username, visitor_num)

            # Create default project
            project, project_created = cls._create_default_project(user, project_slug)

            # Initialize project directory
            success = cls._initialize_project_directory(user, project, project_slug)
            if success:
                created_count += 1
            elif project_created:
                project.delete()

        # Get actual pool status
        existing_users = sum(
            1 for i in range(1, pool_size + 1)
            if User.objects.filter(
                username=f"{cls.VISITOR_USER_PREFIX}{i:03d}"
            ).exists()
        )

        if created_count > 0:
            logger.info(
                f"[VisitorPool] Pool initialization complete: {created_count} new projects created"
            )
        else:
            logger.info(
                f"[VisitorPool] Pool already initialized: {existing_users}/{pool_size} visitor accounts ready"
            )

        return created_count

    @classmethod
    def _check_pool_ready(cls, pool_size: int) -> bool:
        """Check if pool is already fully initialized."""
        for i in range(1, pool_size + 1):
            visitor_num = f"{i:03d}"
            username = f"{cls.VISITOR_USER_PREFIX}{visitor_num}"
            project_slug = "default-project"

            try:
                user = User.objects.get(username=username)
                project = Project.objects.get(slug=project_slug, owner=user)

                # Check directory exists
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
    def _initialize_project_directory(cls, user: User, project: Project, project_slug: str) -> bool:
        """Initialize project directory and writer workspace."""
        from apps.project_app.services.project_filesystem import (
            get_project_filesystem_manager,
        )
        from .workspace_manager import WorkspaceManager

        manager = get_project_filesystem_manager(user)
        project_root = manager.get_project_root_path(project)

        # Create directory if needed
        if not (project_root and project_root.exists()):
            project_path = manager.base_path / project_slug

            # Ensure directory doesn't exist before copying
            if project_path.exists():
                shutil.rmtree(project_path)
                logger.info(f"[VisitorPool] Removed existing directory before template copy")

            # Copy master template
            success = cls._copy_template(project_path)
            if not success:
                return False

            # Update project
            project.git_clone_path = str(project_path)
            project.directory_created = True
            project.save(update_fields=["git_clone_path", "directory_created"])

            logger.info(f"[VisitorPool] Created project: {project_slug} at {project_path}")

            # Initialize writer workspace
            WorkspaceManager.initialize_visitor_writer_workspace(project, Path(project_path))
        else:
            logger.info(f"[VisitorPool] Project directory already exists: {project_root}")

            # Set git_clone_path if not already set
            if not project.git_clone_path:
                project.git_clone_path = str(project_root)
                project.save(update_fields=["git_clone_path"])
                logger.info(f"[VisitorPool] Set git_clone_path for existing project: {project_root}")

            # Initialize writer workspace
            WorkspaceManager.initialize_visitor_writer_workspace(project, project_root)

        return True

    @classmethod
    def reset_all_project_directories(cls, pool_size: int) -> int:
        """
        Reset all visitor project directories to default template state.

        This removes existing directories and re-copies the template.
        Used when re-initializing the pool in development.

        Args:
            pool_size: Number of visitor accounts in pool

        Returns:
            int: Number of directories reset
        """
        reset_count = 0

        for i in range(1, pool_size + 1):
            visitor_num = f"{i:03d}"
            username = f"{cls.VISITOR_USER_PREFIX}{visitor_num}"
            project_slug = "default-project"

            try:
                user = User.objects.get(username=username)
                project = Project.objects.get(slug=project_slug, owner=user)

                from apps.project_app.services.project_filesystem import (
                    get_project_filesystem_manager,
                )
                manager = get_project_filesystem_manager(user)
                project_root = manager.get_project_root_path(project)

                if project_root and project_root.exists():
                    # Remove existing directory
                    shutil.rmtree(project_root)
                    logger.info(f"[VisitorPool] Removed directory for {username}")

                    # Re-copy template
                    success = cls._copy_template(project_root)
                    if success:
                        reset_count += 1
                        logger.info(f"[VisitorPool] Reset directory for {username}")

                        # Re-initialize git repository (clean state)
                        cls._init_git_repo(project_root, username)

                        # Re-initialize writer workspace
                        from .workspace_manager import WorkspaceManager
                        WorkspaceManager.initialize_visitor_writer_workspace(project, project_root)
                    else:
                        logger.error(f"[VisitorPool] Failed to reset directory for {username}")

            except (User.DoesNotExist, Project.DoesNotExist) as e:
                logger.warning(f"[VisitorPool] Skipping reset for {username}: {e}")
            except Exception as e:
                logger.error(f"[VisitorPool] Error resetting {username}: {e}")

        logger.info(f"[VisitorPool] Reset {reset_count} project directories")
        return reset_count

    @classmethod
    def _init_git_repo(cls, project_path: Path, username: str) -> bool:
        """Initialize a clean git repository for the project."""
        import subprocess

        try:
            # Remove existing .git if any (shouldn't exist after rmtree, but be safe)
            git_dir = project_path / '.git'
            if git_dir.exists():
                shutil.rmtree(git_dir)

            # Initialize new git repo
            subprocess.run(
                ['git', 'init'],
                cwd=project_path,
                capture_output=True,
                check=True
            )

            # Configure git user for this repo
            subprocess.run(
                ['git', 'config', 'user.email', f'{username}@visitor.scitex.local'],
                cwd=project_path,
                capture_output=True,
                check=True
            )
            subprocess.run(
                ['git', 'config', 'user.name', username],
                cwd=project_path,
                capture_output=True,
                check=True
            )

            # Add all files and create initial commit
            subprocess.run(
                ['git', 'add', '-A'],
                cwd=project_path,
                capture_output=True,
                check=True
            )
            subprocess.run(
                ['git', 'commit', '-m', 'Initial project setup'],
                cwd=project_path,
                capture_output=True,
                check=True
            )

            logger.info(f"[VisitorPool] Initialized git repo for {username}")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"[VisitorPool] Git init failed for {username}: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"[VisitorPool] Git init error for {username}: {e}")
            return False

    @classmethod
    def _copy_template(cls, project_path: Path) -> bool:
        """Copy master template to project directory."""
        template_master = Path(getattr(
            settings,
            "VISITOR_TEMPLATE_PATH",
            "/app/templates/research-master"
        ))

        try:
            if not template_master.exists():
                logger.warning(
                    f"[VisitorPool] Master template not found at {template_master}, using basic directory"
                )
                from apps.project_app.services.project_filesystem import (
                    get_project_filesystem_manager,
                )
                from django.contrib.auth.models import User
                # This is a fallback - template doesn't exist
                return False
            else:
                logger.info(f"[VisitorPool] Copying template from {template_master}")
                shutil.copytree(template_master, project_path, symlinks=True)
                logger.info(f"[VisitorPool] Template copied successfully")
                return True

        except Exception as e:
            logger.error(f"[VisitorPool] Template copy error: {e}")
            return False
