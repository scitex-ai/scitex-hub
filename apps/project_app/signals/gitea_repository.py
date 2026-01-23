#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-29 04:54:30 (ywatanabe)"

"""
Signals for Gitea repository creation and deletion.

Automatically creates Gitea repositories when Django projects are created.
Automatically deletes Gitea repositories when Django projects are deleted.
"""

import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from ..models import Project
from .project_initialization import _clone_gitea_repo_to_data_dir

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Project)
def create_gitea_repository(sender, instance, created, **kwargs):
    """
    Automatically create Gitea repository when a new Project is created.

    Args:
        sender: The model class (Project)
        instance: The Project instance
        created: Boolean indicating if this is a new instance
        **kwargs: Additional keyword arguments
    """
    # Only create repo for new projects
    if not created:
        return

    # Gitea integration is always enabled (core feature)
    try:
        from apps.gitea_app.api_client import GiteaClient, GiteaAPIError
        import requests.exceptions

        # Initialize Gitea client
        try:
            client = GiteaClient()
        except (
            requests.exceptions.ConnectionError,
            ConnectionRefusedError,
        ) as e:
            logger.warning(
                f"Gitea unavailable during project creation for {instance.slug}: {e}"
            )
            logger.info(
                "Project created without Gitea repository. Repository will be created when Gitea becomes available."
            )
            return

        # Prepare repository data
        repo_name = instance.slug
        description = instance.description or f"SciTeX project: {instance.name}"
        is_private = instance.visibility == "private"

        # Check if repository already exists
        try:
            existing_repo = client.get_repository(
                owner=instance.owner.username, repo=repo_name
            )
            logger.info(
                f"Gitea repository already exists: {instance.owner.username}/{repo_name}"
            )

            # Update project with Gitea info
            instance.gitea_repo_url = existing_repo.get("html_url", "")
            instance.gitea_clone_url = existing_repo.get("clone_url", "")
            instance.save(update_fields=["gitea_repo_url", "gitea_clone_url"])
            return

        except (
            requests.exceptions.ConnectionError,
            ConnectionRefusedError,
        ) as e:
            logger.warning(
                f"Gitea unavailable when checking existing repo for {repo_name}: {e}"
            )
            return
        except GiteaAPIError:
            # Repository doesn't exist, create it
            pass

        # Ensure Gitea user exists before creating repository
        from apps.gitea_app.services.gitea_sync_service import (
            ensure_gitea_user_exists,
        )
        from apps.gitea_app.exceptions import (
            GiteaUserCreationError,
            GiteaConnectionError,
        )

        try:
            ensure_gitea_user_exists(instance.owner)
        except GiteaConnectionError as e:
            logger.warning(f"Gitea unavailable when creating user: {e}")
            logger.info(
                "Project created without Gitea repository. Repository will be created when Gitea becomes available."
            )
            return
        except GiteaUserCreationError as e:
            logger.error(f"Failed to create Gitea user {instance.owner.username}: {e}")
            logger.error(f"Cannot create repository without Gitea user account")
            return

        # Create repository in Gitea under the project owner
        logger.info(
            f"Creating Gitea repository: {instance.owner.username}/{repo_name} (private={is_private})"
        )

        repo = client.create_repository(
            name=repo_name,
            description=description,
            private=is_private,
            auto_init=True,  # Initialize with README
            gitignores="Python",  # Add Python .gitignore
            license="MIT",  # Default license
            readme="Default",
            owner=instance.owner.username,  # Create under specific user
        )

        # Update Django project with Gitea repository information
        instance.gitea_repo_url = repo.get("html_url", "")
        instance.gitea_clone_url = repo.get("clone_url", "")
        instance.gitea_ssh_url = repo.get("ssh_url", "")
        instance.gitea_repo_id = repo.get("id")
        instance.gitea_repo_name = repo.get("name", repo_name)
        instance.git_url = repo.get("clone_url", "")  # HTTPS URL for cloning
        instance.gitea_enabled = True
        instance.save(
            update_fields=[
                "gitea_repo_url",
                "gitea_clone_url",
                "gitea_ssh_url",
                "gitea_repo_id",
                "gitea_repo_name",
                "git_url",
                "gitea_enabled",
            ]
        )

        logger.info(f"✓ Gitea repository created: {instance.gitea_repo_url}")

        # Clone repository to Django data directory
        _clone_gitea_repo_to_data_dir(instance)

    except (requests.exceptions.ConnectionError, ConnectionRefusedError):
        # Gitea unavailable - log warning but don't fail project creation
        logger.warning(f"Gitea unavailable for {instance.slug}: Connection refused")
        logger.info(
            "Project created without Gitea repository. Repository will be created when Gitea becomes available."
        )
    except Exception as e:
        # Log error but don't fail project creation
        logger.error(f"Failed to create Gitea repository for {instance.slug}: {e}")
        logger.exception("Full traceback:")


@receiver(post_delete, sender=Project)
def delete_gitea_repository(sender, instance, **kwargs):
    """
    Automatically delete Gitea repository when a Django Project is deleted.

    Ensures that deleting a project from SciTeX Cloud also removes the
    corresponding repository from Gitea to maintain consistency.

    Args:
        sender: The model class (Project)
        instance: The Project instance being deleted
        **kwargs: Additional keyword arguments
    """
    # Skip if no Gitea repo associated
    if not instance.gitea_repo_url or not instance.gitea_repo_id:
        logger.info(
            f"No Gitea repository associated with project {instance.slug}, skipping deletion"
        )
        return

    try:
        from apps.gitea_app.api_client import GiteaClient, GiteaAPIError
        import requests.exceptions

        logger.info(f"Deleting Gitea repository for project {instance.slug}")

        # Initialize Gitea client
        try:
            client = GiteaClient()
        except (
            requests.exceptions.ConnectionError,
            ConnectionRefusedError,
        ) as e:
            logger.warning(
                f"Gitea unavailable during project deletion for {instance.slug}: {e}"
            )
            logger.warning(
                "Gitea repository was NOT deleted. Please manually delete it or use cleanup command."
            )
            return

        # Delete repository in Gitea
        try:
            client.delete_repository(owner=instance.owner.username, repo=instance.slug)
            logger.info(
                f"✓ Gitea repository deleted: {instance.owner.username}/{instance.slug}"
            )
        except GiteaAPIError as e:
            logger.warning(
                f"Gitea repository may not exist or was already deleted: {instance.owner.username}/{instance.slug}"
            )
            logger.debug(f"Error details: {e}")

    except (requests.exceptions.ConnectionError, ConnectionRefusedError):
        logger.warning(f"Gitea unavailable for {instance.slug}: Connection refused")
        logger.warning(
            "Gitea repository was NOT deleted. Please manually delete it or use cleanup command."
        )
    except Exception as e:
        logger.error(f"Failed to delete Gitea repository for {instance.slug}: {e}")
        logger.exception("Full traceback:")


# EOF
