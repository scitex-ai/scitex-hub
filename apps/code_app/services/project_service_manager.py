#!/usr/bin/env python3
"""
Project Service Manager
Manages services (TensorBoard, Jupyter, etc.) running for projects
"""

import subprocess
import psutil
import socket
from typing import Optional, Dict, Any
from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone
from apps.code_app.models import ProjectService


class ProjectServiceManager:
    """Manage services for projects with security and resource management."""

    # Safe port ranges for services (per project)
    BASE_PORT = 10000
    PORTS_PER_PROJECT = 100  # Each project gets 100 ports
    MAX_SERVICES_PER_PROJECT = 10

    # Service commands
    SERVICE_COMMANDS = {
        "tensorboard": [
            "tensorboard",
            "--logdir", "{workspace}/logs",
            "--port", "{port}",
            "--host", "127.0.0.1",
            "--bind_all"
        ],
        "jupyter": [
            "jupyter", "lab",
            "--port", "{port}",
            "--ip", "127.0.0.1",
            "--no-browser",
            "--notebook-dir", "{workspace}",
            "--ServerApp.token=",  # No token for now
            "--ServerApp.password="
        ],
        "mlflow": [
            "mlflow", "ui",
            "--port", "{port}",
            "--host", "127.0.0.1",
            "--backend-store-uri", "{workspace}/mlruns"
        ],
        "streamlit": [
            "streamlit", "run",
            "{workspace}/app.py",
            "--server.port", "{port}",
            "--server.address", "127.0.0.1",
            "--server.headless", "true"
        ],
    }

    def start_service(
        self,
        user,
        project,
        service_type: str,
        config: Optional[Dict[str, Any]] = None
    ) -> ProjectService:
        """
        Start a service for a project.

        Args:
            user: User starting the service
            project: Project to start service for
            service_type: Type of service (tensorboard, jupyter, etc.)
            config: Optional service configuration

        Returns:
            ProjectService instance

        Raises:
            PermissionDenied: If user doesn't have access
            ValidationError: If invalid service type or limits exceeded
        """
        # 1. Check user has access to project
        if not self._has_project_access(user, project):
            raise PermissionDenied("You don't have access to this project")

        # 2. Check service type is valid
        if service_type not in self.SERVICE_COMMANDS:
            raise ValidationError(f"Invalid service type: {service_type}")

        # 3. Check if service already running
        existing = ProjectService.objects.filter(
            project=project,
            service_type=service_type,
            status__in=["starting", "running"]
        ).first()

        if existing:
            return existing  # Return existing service

        # 4. Check service limits
        active_services_count = ProjectService.objects.filter(
            project=project,
            status__in=["starting", "running"]
        ).count()

        if active_services_count >= self.MAX_SERVICES_PER_PROJECT:
            raise ValidationError(
                f"Maximum {self.MAX_SERVICES_PER_PROJECT} services per project"
            )

        # 5. Allocate port
        port = self._allocate_port(project)

        # 6. Start service process
        process = self._start_service_process(
            service_type=service_type,
            port=port,
            workspace=self._get_project_workspace(project),
            config=config or {}
        )

        # 7. Register service
        service = ProjectService.objects.create(
            project=project,
            user=user,
            service_type=service_type,
            port=port,
            process_id=process.pid if process else None,
            status="running" if process else "error",
            config=config or {}
        )

        return service

    def stop_service(self, user, service_id: str) -> bool:
        """
        Stop a running service.

        Args:
            user: User stopping the service
            service_id: Service UUID

        Returns:
            True if stopped successfully

        Raises:
            PermissionDenied: If user doesn't own the service
        """
        try:
            service = ProjectService.objects.get(service_id=service_id)
        except ProjectService.DoesNotExist:
            return False

        # Check ownership
        if not self._has_project_access(user, service.project):
            raise PermissionDenied("You don't have access to this service")

        # Kill process if running
        if service.process_id:
            try:
                process = psutil.Process(service.process_id)
                process.terminate()
                process.wait(timeout=5)
            except (psutil.NoSuchProcess, psutil.TimeoutExpired):
                pass

        # Update service status
        service.status = "stopped"
        service.stopped_at = timezone.now()
        service.save(update_fields=["status", "stopped_at"])

        return True

    def cleanup_idle_services(self, idle_hours: int = 4) -> int:
        """
        Clean up services that haven't been accessed recently.

        Args:
            idle_hours: Hours of idleness before cleanup

        Returns:
            Number of services cleaned up
        """
        from datetime import timedelta

        cutoff_time = timezone.now() - timedelta(hours=idle_hours)

        idle_services = ProjectService.objects.filter(
            status__in=["starting", "running"],
            last_accessed__lt=cutoff_time
        )

        count = 0
        for service in idle_services:
            try:
                # Try to stop gracefully
                if service.process_id:
                    try:
                        process = psutil.Process(service.process_id)
                        process.terminate()
                    except psutil.NoSuchProcess:
                        pass

                service.status = "stopped"
                service.stopped_at = timezone.now()
                service.save(update_fields=["status", "stopped_at"])
                count += 1
            except Exception as e:
                print(f"Error cleaning up service {service.service_id}: {e}")

        return count

    def _allocate_port(self, project) -> int:
        """
        Allocate a free port in the project's range.

        Args:
            project: Project to allocate port for

        Returns:
            Available port number

        Raises:
            ValidationError: If no free ports available
        """
        # Calculate project's port range
        project_base = self.BASE_PORT + (project.id * self.PORTS_PER_PROJECT)

        # Get used ports
        used_ports = set(
            ProjectService.objects.filter(
                project=project,
                status__in=["starting", "running"]
            ).values_list("port", flat=True)
        )

        # Find free port
        for offset in range(self.PORTS_PER_PROJECT):
            port = project_base + offset
            if port not in used_ports and self._is_port_available(port):
                return port

        raise ValidationError(
            f"No free ports available for project (range: {project_base}-{project_base + self.PORTS_PER_PROJECT - 1})"
        )

    def _is_port_available(self, port: int) -> bool:
        """Check if port is available on localhost."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", port))
                return True
        except OSError:
            return False

    def _start_service_process(
        self,
        service_type: str,
        port: int,
        workspace: str,
        config: Dict[str, Any]
    ) -> Optional[subprocess.Popen]:
        """
        Start the actual service process.

        Args:
            service_type: Type of service
            port: Port to run on
            workspace: Project workspace directory
            config: Service configuration

        Returns:
            Process object or None if failed
        """
        # Get command template
        cmd_template = self.SERVICE_COMMANDS.get(service_type)
        if not cmd_template:
            return None

        # Format command with parameters
        cmd = [
            part.format(port=port, workspace=workspace, **config)
            for part in cmd_template
        ]

        try:
            # Start process
            process = subprocess.Popen(
                cmd,
                cwd=workspace,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True  # Detach from parent
            )
            return process
        except Exception as e:
            print(f"Failed to start {service_type}: {e}")
            return None

    def _get_project_workspace(self, project) -> str:
        """Get workspace directory for project."""
        # This should be adjusted based on your actual workspace structure
        from pathlib import Path
        base = Path("/workspace") if Path("/workspace").exists() else Path.home() / "workspace"
        return str(base / project.owner.username / project.slug)

    def _has_project_access(self, user, project) -> bool:
        """Check if user has access to project."""
        # Owner always has access
        if project.owner == user:
            return True

        # Check if user is a collaborator
        return project.memberships.filter(user=user).exists()

    def is_port_in_allowed_range(self, port: int) -> bool:
        """Check if port is in the allowed range for services."""
        max_port = self.BASE_PORT + (1000 * self.PORTS_PER_PROJECT)  # Allow up to 1000 projects
        return self.BASE_PORT <= port < max_port
