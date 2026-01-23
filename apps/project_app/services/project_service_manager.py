"""
Project Service Manager

Unified manager for local and remote projects.

This provides a single API for working with projects regardless of type:
- Local projects: Git-enabled, Gitea repositories
- Remote projects: SSHFS mounts, no Git

Example usage:
    >>> from apps.project_app.models import Project
    >>> from apps.project_app.services.project_service_manager import ProjectServiceManager
    >>>
    >>> project = Project.objects.get(slug='my-project')
    >>> manager = ProjectServiceManager(project)
    >>>
    >>> # Get project path (works for both local and remote)
    >>> path = manager.get_project_path()
    >>>
    >>> # Initialize SciTeX structure (works for both)
    >>> success, stats, error = manager.initialize_scitex_structure()
"""

import subprocess
import logging
import shutil
import re
from pathlib import Path
from typing import Tuple, Optional, Dict
from django.conf import settings

logger = logging.getLogger(__name__)


class ProjectServiceManager:
    """
    Unified project manager for local and remote projects.

    Handles common operations that work across both project types.
    """

    def __init__(self, project):
        """
        Initialize project manager.

        Args:
            project: Project instance (local or remote)
        """
        self.project = project

    def get_project_path(self) -> Path:
        """
        Get project filesystem path (local or remote mount point).

        Returns:
            Path - Local Gitea path or SSHFS mount point

        Example:
            >>> manager = ProjectServiceManager(project)
            >>> path = manager.get_project_path()
            >>> files = list(path.rglob("*.py"))
        """
        if self.project.project_type == 'local':
            # Return Gitea repository path
            from apps.project_app.services.project_filesystem import (
                get_project_filesystem_manager
            )
            dir_mgr = get_project_filesystem_manager(self.project.owner)
            return dir_mgr.get_project_root_path(self.project)

        elif self.project.project_type == 'remote':
            # Return SSHFS mount point (auto-mount if needed)
            from apps.project_app.services.remote_project_manager import RemoteProjectManager
            remote_mgr = RemoteProjectManager(self.project)

            # Ensure mounted
            success, error = remote_mgr.ensure_mounted()
            if not success:
                raise RuntimeError(f"Failed to mount remote project: {error}")

            # Return mount point
            return remote_mgr.mount_point

        else:
            raise ValueError(f"Unknown project type: {self.project.project_type}")

    def initialize_scitex_structure(self) -> Tuple[bool, Dict, Optional[str]]:
        """
        Sync SciTeX template structure to project (local or remote).

        Dispatches to appropriate implementation based on project type.

        Returns:
            (success, stats, error_message)

        Stats dict contains:
            - files_created: Number of new files created
            - files_skipped: Number of existing files skipped
            - bytes_transferred: Total bytes synced

        Example:
            >>> manager = ProjectServiceManager(project)
            >>> success, stats, error = manager.initialize_scitex_structure()
            >>> if success:
            >>>     print(f"Created {stats['files_created']} files")
        """
        if self.project.project_type == 'local':
            return self._initialize_local()
        elif self.project.project_type == 'remote':
            return self._initialize_remote()
        else:
            return False, {}, f"Unknown project type: {self.project.project_type}"

    def _initialize_local(self) -> Tuple[bool, Dict, Optional[str]]:
        """
        Initialize SciTeX structure on LOCAL project.

        Copies template files from templates/research-master/scitex/ to project.
        Non-destructive: Won't override existing files.

        Returns:
            (success, stats, error_message)
        """
        # Get template directory
        template_dir = Path(settings.BASE_DIR) / 'templates' / 'research-master' / 'scitex'

        if not template_dir.exists():
            return False, {}, f"Template not found: {template_dir}"

        # Get project directory (from Gitea)
        try:
            project_path = self.get_project_path()
        except Exception as e:
            return False, {}, f"Failed to get project path: {str(e)}"

        if not project_path or not project_path.exists():
            return False, {}, "Project directory not found"

        # Target: {project_path}/scitex/
        target_dir = project_path / 'scitex'

        try:
            stats = {
                'files_created': 0,
                'files_skipped': 0,
                'bytes_transferred': 0,
            }

            # Walk through template and copy files (non-destructive)
            for src_file in template_dir.rglob('*'):
                if src_file.is_file():
                    # Relative path within scitex/
                    rel_path = src_file.relative_to(template_dir)
                    dest_file = target_dir / rel_path

                    # Skip if exists (non-destructive)
                    if dest_file.exists():
                        stats['files_skipped'] += 1
                        continue

                    # Create parent directories
                    dest_file.parent.mkdir(parents=True, exist_ok=True)

                    # Copy file
                    shutil.copy2(src_file, dest_file)

                    stats['files_created'] += 1
                    stats['bytes_transferred'] += src_file.stat().st_size

            logger.info(
                f"✅ SciTeX structure initialized (local): "
                f"{self.project.owner.username}/{self.project.slug} - "
                f"{stats['files_created']} files created"
            )

            return True, stats, None

        except Exception as e:
            logger.error(f"Failed to initialize local structure: {e}")
            return False, {}, str(e)

    def _initialize_remote(self) -> Tuple[bool, Dict, Optional[str]]:
        """
        Sync SciTeX template structure to remote filesystem.

        Uses rsync to sync template to remote, with --ignore-existing (non-destructive).

        Creates scitex/ directory on remote with standard structure:
        - scitex/vis/
        - scitex/writer/
        - scitex/scholar/
        - scitex/code/
        - etc.

        Non-destructive: Won't override existing files.

        Returns:
            (success, stats, error_message)
        """
        # Get template directory
        template_dir = Path(settings.BASE_DIR) / 'templates' / 'research-master' / 'scitex'

        if not template_dir.exists():
            return False, {}, f"Template not found: {template_dir}"

        # Get remote config
        if not hasattr(self.project, 'remote_config') or not self.project.remote_config:
            return False, {}, "No remote configuration"

        config = self.project.remote_config

        # Get SSH key
        ssh_key_path = config.remote_credential.private_key_path

        # Remote target
        remote_target = (
            f"{config.ssh_username}@{config.ssh_host}:"
            f"{config.remote_path}/scitex/"
        )

        # Rsync command - NON-DESTRUCTIVE
        cmd = [
            "rsync",
            "-avz",
            "--progress",
            "--ignore-existing",    # Don't override existing files ✅
            "--stats",              # Get statistics
            "-e", f"ssh -p {config.ssh_port} -i {ssh_key_path} -o StrictHostKeyChecking=accept-new",
            f"{template_dir}/",     # Source: SciTeX template
            remote_target,          # Target: remote/scitex/
        ]

        try:
            logger.info(
                f"Initializing SciTeX structure on remote: "
                f"{config.ssh_username}@{config.ssh_host}:{config.remote_path}"
            )

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minutes
                check=True
            )

            # Parse rsync stats from output
            stats = self._parse_rsync_stats(result.stdout)

            logger.info(
                f"✅ SciTeX structure initialized (remote): "
                f"{stats['files_created']} files created, "
                f"{stats['files_skipped']} files skipped"
            )

            return True, stats, None

        except subprocess.CalledProcessError as e:
            error_msg = f"Rsync failed: {e.stderr}"
            logger.error(error_msg)
            return False, {}, error_msg

        except subprocess.TimeoutExpired:
            return False, {}, "Rsync timeout (5 minutes)"

        except Exception as e:
            logger.error(f"Unexpected rsync error: {str(e)}")
            return False, {}, str(e)

    def _parse_rsync_stats(self, output: str) -> Dict:
        """
        Parse rsync --stats output.

        Args:
            output: Rsync stdout output

        Returns:
            Stats dictionary
        """
        stats = {
            'files_created': 0,
            'files_skipped': 0,
            'bytes_transferred': 0,
        }

        # Extract statistics from rsync output
        # "Number of created files: 42"
        match = re.search(r'Number of created files:\s*(\d+)', output)
        if match:
            stats['files_created'] = int(match.group(1))

        # "Number of regular files transferred: 15"
        match = re.search(r'Number of regular files transferred:\s*(\d+)', output)
        if match:
            stats['files_created'] = int(match.group(1))

        # "Total transferred file size: 123456 bytes"
        match = re.search(r'Total transferred file size:\s*([\d,]+)', output)
        if match:
            stats['bytes_transferred'] = int(match.group(1).replace(',', ''))

        return stats
