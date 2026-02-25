#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-14 17:45:00 (ywatanabe)"
# File: ./apps/workspace_app/services/container_manager.py

"""
User Container Manager

Manages Docker containers for user computational workspaces.
Handles container lifecycle: creation, starting, stopping, cleanup.
"""

try:
    import docker
except ImportError:
    docker = None  # Optional dependency for container management
import logging
from typing import Optional, Tuple

from django.contrib.auth.models import User
from django.utils import timezone

logger = logging.getLogger(__name__)


class UserContainerManager:
    """
    Manages user workspace containers

    Each user gets their own isolated Docker container with:
    - Python + scientific packages
    - Their project data mounted at /home/user
    - Resource limits (CPU, memory)
    - Network access

    Usage:
        manager = UserContainerManager()
        container = manager.get_or_create_container(user)
        output = manager.exec_command(user, ["python", "script.py"])
        manager.stop_container(user)
    """

    # Configuration
    IMAGE_NAME = "scitex-user-workspace:latest"
    NETWORK_NAME = "scitex-cloud-dev_scitex-dev"  # Same network as web/db containers

    # Resource limits
    DEFAULT_CPU_QUOTA = 200000  # 2 CPU cores (100000 = 1 core)
    DEFAULT_MEMORY_LIMIT = "8g"  # 8 GB

    # Timeouts
    IDLE_TIMEOUT_MINUTES = 30

    def __init__(self):
        """Initialize container manager with Docker client"""
        try:
            self.client = docker.from_env()
            logger.info("UserContainerManager initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Docker client: {e}")
            raise

    def _get_container_name(self, user: User) -> str:
        """Get standardized container name for user"""
        return f"scitex-user-{user.username}"

    def _get_user_data_path(self, user: User) -> str:
        """Get path to user's data directory"""
        # This matches the existing project data structure
        return f"/app/data/users/{user.username}"

    def get_or_create_container(
        self, user: User
    ) -> "docker.models.containers.Container":
        """
        Get existing container or create new one

        Args:
            user: Django User instance

        Returns:
            Running Docker container

        Raises:
            docker.errors.DockerException: If Docker operation fails
        """
        container_name = self._get_container_name(user)

        try:
            # Try to get existing container
            container = self.client.containers.get(container_name)

            # If stopped, start it
            if container.status != "running":
                logger.info(f"Starting existing container for {user.username}")
                container.start()
                self._update_workspace_state(user, container, started=True)
            else:
                logger.debug(f"Using running container for {user.username}")
                self._mark_activity(user)

            return container

        except docker.errors.NotFound:
            # Container doesn't exist, create it
            logger.info(f"Creating new container for {user.username}")
            return self._create_container(user)

    def _create_container(self, user: User) -> "docker.models.containers.Container":
        """
        Create new container for user

        Args:
            user: Django User instance

        Returns:
            Created and running container
        """
        container_name = self._get_container_name(user)
        user_data_path = self._get_user_data_path(user)

        try:
            container = self.client.containers.run(
                self.IMAGE_NAME,
                name=container_name,
                detach=True,
                stdin_open=True,
                tty=True,
                # Resource limits
                mem_limit=self.DEFAULT_MEMORY_LIMIT,
                cpu_quota=self.DEFAULT_CPU_QUOTA,
                # Mount user's data
                volumes={user_data_path: {"bind": "/home/user", "mode": "rw"}},
                # Network - same as other SciTeX containers
                network=self.NETWORK_NAME,
                # Environment variables
                environment={
                    "USER": "user",
                    "HOME": "/home/user",
                    "SCITEX_USERNAME": user.username,
                    "SCITEX_USER_ID": user.id,
                },
                # Labels for identification
                labels={
                    "scitex.user": user.username,
                    "scitex.user_id": str(user.id),
                    "scitex.type": "user-workspace",
                },
            )

            logger.info(f"✓ Created container for {user.username}: {container.id[:12]}")
            self._update_workspace_state(user, container, started=True)

            return container

        except docker.errors.ImageNotFound:
            logger.error(f"Image not found: {self.IMAGE_NAME}. Please build it first.")
            raise
        except Exception as e:
            logger.error(f"Failed to create container for {user.username}: {e}")
            raise

    def stop_container(self, user: User, timeout: int = 10) -> bool:
        """
        Stop user's container

        Args:
            user: Django User instance
            timeout: Seconds to wait before forcing stop

        Returns:
            True if stopped, False if not found
        """
        container_name = self._get_container_name(user)

        try:
            container = self.client.containers.get(container_name)

            if container.status == "running":
                logger.info(f"Stopping container for {user.username}")
                container.stop(timeout=timeout)
                self._update_workspace_state(user, container, started=False)
                return True
            else:
                logger.debug(f"Container already stopped for {user.username}")
                return True

        except docker.errors.NotFound:
            logger.debug(f"No container found for {user.username}")
            return False

    def remove_container(self, user: User, force: bool = False) -> bool:
        """
        Remove user's container completely

        Args:
            user: Django User instance
            force: Force removal even if running

        Returns:
            True if removed, False if not found
        """
        container_name = self._get_container_name(user)

        try:
            container = self.client.containers.get(container_name)
            logger.info(f"Removing container for {user.username}")
            container.remove(force=force)
            self._clear_workspace_state(user)
            return True

        except docker.errors.NotFound:
            logger.debug(f"No container to remove for {user.username}")
            return False

    def exec_command(
        self, user: User, command: list, workdir: str = "/home/user"
    ) -> Tuple[int, str]:
        """
        Execute command in user's container

        Args:
            user: Django User instance
            command: Command to execute as list (e.g., ["python", "script.py"])
            workdir: Working directory for command

        Returns:
            Tuple of (exit_code, output)
        """
        container = self.get_or_create_container(user)

        try:
            result = container.exec_run(
                command,
                workdir=workdir,
                stdout=True,
                stderr=True,
            )

            self._mark_activity(user)

            return result.exit_code, result.output.decode("utf-8")

        except Exception as e:
            logger.error(
                f"Failed to execute command in {user.username}'s container: {e}"
            )
            raise

    def get_container_status(self, user: User) -> Optional[dict]:
        """
        Get container status information

        Args:
            user: Django User instance

        Returns:
            Dict with status info or None if not found
        """
        container_name = self._get_container_name(user)

        try:
            container = self.client.containers.get(container_name)

            return {
                "id": container.id,
                "name": container.name,
                "status": container.status,
                "created": container.attrs["Created"],
                "image": container.image.tags[0] if container.image.tags else None,
            }

        except docker.errors.NotFound:
            return None

    def list_idle_containers(self, idle_minutes: int = None) -> list:
        """
        List containers that have been idle

        Args:
            idle_minutes: Minutes of inactivity (default: IDLE_TIMEOUT_MINUTES)

        Returns:
            List of (user, container) tuples for idle containers
        """
        if idle_minutes is None:
            idle_minutes = self.IDLE_TIMEOUT_MINUTES

        # Import here to avoid circular dependency
        from apps.workspace_app.models import UserWorkspace

        cutoff_time = timezone.now() - timezone.timedelta(minutes=idle_minutes)

        idle_workspaces = UserWorkspace.objects.filter(
            is_running=True, last_activity_at__lt=cutoff_time
        )

        idle_list = []
        for workspace in idle_workspaces:
            try:
                container = self.client.containers.get(workspace.container_name)
                if container.status == "running":
                    idle_list.append((workspace.user, container))
            except docker.errors.NotFound:
                # Container doesn't exist, update state
                workspace.is_running = False
                workspace.save()

        return idle_list

    def cleanup_idle_containers(self, idle_minutes: int = None) -> int:
        """
        Stop idle containers to free resources

        Args:
            idle_minutes: Minutes of inactivity before stopping

        Returns:
            Number of containers stopped
        """
        idle_containers = self.list_idle_containers(idle_minutes)
        stopped_count = 0

        for user, container in idle_containers:
            try:
                self.stop_container(user)
                stopped_count += 1
                logger.info(f"Stopped idle container for {user.username}")
            except Exception as e:
                logger.error(f"Failed to stop idle container for {user.username}: {e}")

        return stopped_count

    # Helper methods for state tracking

    def _update_workspace_state(
        self, user: User, container: "docker.models.containers.Container", started: bool
    ):
        """Update UserWorkspace model with container state"""
        from apps.workspace_app.models import UserWorkspace

        workspace, created = UserWorkspace.objects.get_or_create(user=user)
        workspace.container_id = container.id
        workspace.container_name = container.name

        if started:
            workspace.mark_started()
        else:
            workspace.mark_stopped()

    def _mark_activity(self, user: User):
        """Mark user workspace as recently active"""
        from apps.workspace_app.models import UserWorkspace

        try:
            workspace = UserWorkspace.objects.get(user=user)
            workspace.mark_activity()
        except UserWorkspace.DoesNotExist:
            pass

    def _clear_workspace_state(self, user: User):
        """Clear workspace state when container is removed"""
        from apps.workspace_app.models import UserWorkspace

        try:
            workspace = UserWorkspace.objects.get(user=user)
            workspace.container_id = None
            workspace.container_name = None
            workspace.is_running = False
            workspace.save()
        except UserWorkspace.DoesNotExist:
            pass


# EOF
