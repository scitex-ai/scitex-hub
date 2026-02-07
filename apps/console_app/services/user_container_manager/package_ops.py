#!/usr/bin/env python3
"""
Package installation operations for User Container Manager
"""

import subprocess
import logging
from typing import Dict, Any, List
from django.contrib.auth.models import User

logger = logging.getLogger(__name__)


class PackageOperations:
    """
    Package installation operations

    Handles:
    - pip package installation
    - apt package installation
    - conda package installation
    """

    def __init__(self, config, path_utils):
        self.config = config
        self.path_utils = path_utils

    def install_package(
        self,
        user: User,
        package_manager: str,
        packages: List[str]
    ) -> Dict[str, Any]:
        """
        Install packages to user's sandbox

        Args:
            user: Django user
            package_manager: 'pip', 'apt', or 'conda'
            packages: List of package names

        Returns:
            Dict with success status and output
        """
        sandbox_path = self.path_utils.get_sandbox_path(user)

        if not sandbox_path.exists():
            return {
                'success': False,
                'message': 'Sandbox does not exist. Create one first.'
            }

        # Build install command
        if package_manager == 'pip':
            packages_str = ' '.join(packages)
            install_cmd = f"pip install --no-cache-dir {packages_str}"
        elif package_manager == 'apt':
            packages_str = ' '.join(packages)
            install_cmd = f"apt-get update && apt-get install -y {packages_str}"
        elif package_manager == 'conda':
            packages_str = ' '.join(packages)
            install_cmd = f"conda install -y {packages_str}"
        else:
            return {
                'success': False,
                'message': f'Invalid package manager: {package_manager}'
            }

        # Execute in sandbox with fakeroot
        cmd = [
            self.config.container_cmd, "exec",
            "--fakeroot",
            "--writable",
            str(sandbox_path),
            "/bin/bash", "-c",
            install_cmd
        ]

        try:
            logger.info(
                f"Installing {packages} with {package_manager} "
                f"for user {user.username}"
            )

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minutes for package installation
                check=True
            )

            return {
                'success': True,
                'packages': packages,
                'package_manager': package_manager,
                'stdout': result.stdout,
                'message': f'Successfully installed: {", ".join(packages)}'
            }

        except subprocess.CalledProcessError as e:
            logger.error(
                f"Package installation failed for {user.username}: {e.stderr}"
            )
            return {
                'success': False,
                'packages': packages,
                'stderr': e.stderr,
                'message': f'Installation failed. See stderr for details.'
            }

        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'packages': packages,
                'message': 'Installation timed out after 5 minutes'
            }

# EOF
