#!/usr/bin/env python3
"""
Container operations for User Container Manager
"""

import subprocess
import logging
import shutil
from typing import Dict, Any
from django.contrib.auth.models import User

logger = logging.getLogger(__name__)


class ContainerOperations:
    """
    Container build and management operations

    Handles:
    - Sandbox creation
    - Container finalization
    - Definition file builds
    - Container deletion
    """

    def __init__(self, config, path_utils, stats_manager):
        self.config = config
        self.path_utils = path_utils
        self.stats_manager = stats_manager

    def create_sandbox(self, user: User) -> Dict[str, Any]:
        """
        Create writable sandbox for user to customize

        Args:
            user: Django user

        Returns:
            Dict with success status and message
        """
        # Check rate limit
        can_build, reason = self.stats_manager.check_build_rate_limit(user)
        if not can_build:
            return {'success': False, 'message': reason}

        sandbox_path = self.path_utils.get_sandbox_path(user)

        # Check if sandbox already exists
        if sandbox_path.exists():
            return {
                'success': False,
                'message': 'Sandbox already exists. Finalize or delete it first.'
            }

        # Create sandbox from base image
        cmd = [
            self.config.container_cmd, "build",
            "--sandbox",
            "--fakeroot",
            str(sandbox_path),
            str(self.config.base_image)
        ]

        try:
            logger.info(f"Creating sandbox for user {user.username}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.config.max_build_time,
                check=True
            )

            self.stats_manager.increment_build_count(user)

            return {
                'success': True,
                'sandbox_path': str(sandbox_path),
                'message': 'Sandbox created successfully. You can now customize it.',
                'next_steps': [
                    'Install packages with pip or apt',
                    'Test your changes',
                    'Finalize to create permanent container'
                ]
            }

        except subprocess.CalledProcessError as e:
            logger.error(f"Sandbox creation failed for {user.username}: {e.stderr}")
            # Clean up partial sandbox
            if sandbox_path.exists():
                shutil.rmtree(sandbox_path, ignore_errors=True)

            return {
                'success': False,
                'message': f'Failed to create sandbox: {e.stderr}',
                'stderr': e.stderr
            }

        except subprocess.TimeoutExpired:
            logger.error(f"Sandbox creation timeout for {user.username}")
            if sandbox_path.exists():
                shutil.rmtree(sandbox_path, ignore_errors=True)

            return {
                'success': False,
                'message': f'Build timed out after {self.config.max_build_time} seconds'
            }

    def finalize_sandbox(self, user: User) -> Dict[str, Any]:
        """
        Convert sandbox to final .sif container

        Args:
            user: Django user

        Returns:
            Dict with success status
        """
        sandbox_path = self.path_utils.get_sandbox_path(user)
        output_sif = self.path_utils.get_user_container_path(user)

        if not sandbox_path.exists():
            return {
                'success': False,
                'message': 'No sandbox to finalize. Create one first.'
            }

        # Check if would exceed size limit
        sandbox_size = sum(
            f.stat().st_size
            for f in sandbox_path.rglob('*')
            if f.is_file()
        )

        if sandbox_size > self.config.max_container_size:
            size_gb = sandbox_size / 1024**3
            limit_gb = self.config.max_container_size / 1024**3
            return {
                'success': False,
                'message': f'Sandbox too large ({size_gb:.1f}GB > {limit_gb}GB limit)'
            }

        # Build final container
        cmd = [
            self.config.container_cmd, "build",
            "--fakeroot",
            str(output_sif),
            str(sandbox_path)
        ]

        try:
            logger.info(f"Finalizing sandbox for user {user.username}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.config.max_build_time,
                check=True
            )

            # Check final size
            final_size = output_sif.stat().st_size
            if final_size > self.config.max_container_size:
                output_sif.unlink()
                return {
                    'success': False,
                    'message': f'Container exceeds size limit'
                }

            # Remove sandbox after successful build
            shutil.rmtree(sandbox_path)

            return {
                'success': True,
                'container_path': str(output_sif),
                'size_mb': final_size / 1024**2,
                'message': 'Container finalized successfully. Sandbox removed.'
            }

        except subprocess.CalledProcessError as e:
            logger.error(f"Finalization failed for {user.username}: {e.stderr}")
            return {
                'success': False,
                'message': f'Finalization failed: {e.stderr}',
                'stderr': e.stderr
            }

        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'message': f'Build timed out after {self.config.max_build_time} seconds'
            }

    def build_from_definition(
        self,
        user: User,
        definition_content: str
    ) -> Dict[str, Any]:
        """
        Build custom container from user's definition file

        Args:
            user: Django user
            definition_content: Singularity/Apptainer definition file content

        Returns:
            Dict with success status
        """
        # Check rate limit
        can_build, reason = self.stats_manager.check_build_rate_limit(user)
        if not can_build:
            return {'success': False, 'message': reason}

        user_dir = self.path_utils.get_user_dir(user)
        def_file = user_dir / "user-container.def"
        output_sif = self.path_utils.get_user_container_path(user)

        # Save definition file
        def_file.write_text(definition_content)

        # Build container
        cmd = [
            self.config.container_cmd, "build",
            "--fakeroot",
            str(output_sif),
            str(def_file)
        ]

        try:
            logger.info(f"Building container from definition for {user.username}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.config.max_build_time,
                check=True
            )

            # Check size
            size = output_sif.stat().st_size
            if size > self.config.max_container_size:
                output_sif.unlink()
                return {
                    'success': False,
                    'message': f'Container too large ({size/1024**3:.1f}GB > {self.config.max_container_size/1024**3}GB limit)'
                }

            self.stats_manager.increment_build_count(user)

            return {
                'success': True,
                'container_path': str(output_sif),
                'size_mb': size / 1024**2,
                'message': 'Custom container built successfully',
                'build_log': result.stdout
            }

        except subprocess.CalledProcessError as e:
            logger.error(f"Build failed for {user.username}: {e.stderr}")
            if output_sif.exists():
                output_sif.unlink()

            return {
                'success': False,
                'message': f'Build failed',
                'stderr': e.stderr,
                'stdout': e.stdout if hasattr(e, 'stdout') else ''
            }

        except subprocess.TimeoutExpired:
            logger.error(f"Build timeout for {user.username}")
            if output_sif.exists():
                output_sif.unlink()

            return {
                'success': False,
                'message': f'Build timed out after {self.config.max_build_time} seconds'
            }

    def delete_custom_container(self, user: User) -> Dict[str, Any]:
        """Delete user's custom container and sandbox"""
        user_dir = self.path_utils.get_user_dir(user)
        container_path = self.path_utils.get_user_container_path(user)
        sandbox_path = self.path_utils.get_sandbox_path(user)

        deleted = []

        if container_path.exists():
            container_path.unlink()
            deleted.append('container')

        if sandbox_path.exists():
            shutil.rmtree(sandbox_path)
            deleted.append('sandbox')

        if deleted:
            return {
                'success': True,
                'message': f'Deleted: {", ".join(deleted)}',
                'deleted': deleted
            }
        else:
            return {
                'success': False,
                'message': 'No custom container or sandbox found'
            }

# EOF
