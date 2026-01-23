#!/usr/bin/env python3
"""
Environment Manager - Core environment management functionality
"""

import os
import json
import subprocess
import tempfile
import venv
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import logging

from django.conf import settings
from django.utils import timezone
from django.contrib.auth.models import User

from .models import Environment, PackageRequirement


logger = logging.getLogger(__name__)


class EnvironmentManager:
    """Manages Python execution environments."""

    def __init__(self, user: User):
        self.user = user
        self.base_path = Path(settings.MEDIA_ROOT) / "environments" / str(user.id)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.metadata_file = self.base_path / "environments.json"
        self._environments: Dict[str, Environment] = {}
        self._load_environments()

    def _load_environments(self):
        """Load existing environments from metadata file."""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file) as f:
                    data = json.load(f)

                for env_data in data.get("environments", []):
                    env = Environment.from_dict(env_data, self.user)
                    self._environments[env.env_id] = env

            except Exception as e:
                logger.error(
                    f"Error loading environments for user {self.user.username}: {e}"
                )

    def _save_environments(self):
        """Save environments metadata to file."""
        try:
            data = {
                "environments": [env.to_dict() for env in self._environments.values()],
                "updated_at": timezone.now().isoformat(),
            }

            with open(self.metadata_file, "w") as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            logger.error(
                f"Error saving environments for user {self.user.username}: {e}"
            )

    def create_environment(
        self, name: str, requirements: Optional[List[str]] = None
    ) -> Environment:
        """Create a new Python environment."""
        env_id = str(uuid.uuid4())
        env = Environment(env_id, self.user, name)

        # Add custom requirements
        if requirements:
            for req_str in requirements:
                try:
                    req = PackageRequirement.from_string(req_str)
                    env.add_requirement(req)
                except Exception as e:
                    logger.warning(f"Invalid requirement '{req_str}': {e}")

        self._environments[env_id] = env
        self._save_environments()

        logger.info(
            f"Created environment '{name}' ({env_id}) for user {self.user.username}"
        )
        return env

    def get_environment(self, env_id: str) -> Optional[Environment]:
        """Get environment by ID."""
        return self._environments.get(env_id)

    def list_environments(self) -> List[Environment]:
        """List all user environments."""
        return list(self._environments.values())

    def delete_environment(self, env_id: str) -> bool:
        """Delete an environment."""
        if env_id not in self._environments:
            return False

        env = self._environments[env_id]

        # Remove environment directory if it exists
        if env.env_path.exists():
            import shutil

            try:
                shutil.rmtree(env.env_path)
            except Exception as e:
                logger.error(
                    f"Error removing environment directory {env.env_path}: {e}"
                )

        # Remove from memory and save
        del self._environments[env_id]
        self._save_environments()

        logger.info(f"Deleted environment {env_id} for user {self.user.username}")
        return True

    def setup_environment(self, env_id: str) -> Tuple[bool, str]:
        """Set up the Python virtual environment with packages."""
        env = self.get_environment(env_id)
        if not env:
            return False, "Environment not found"

        try:
            # Create virtual environment
            venv.create(env.env_path, with_pip=True, clear=True)

            # Get pip executable path
            pip_path = env.env_path / "bin" / "pip"
            if not pip_path.exists():  # Windows
                pip_path = env.env_path / "Scripts" / "pip.exe"

            # Upgrade pip
            subprocess.run(
                [str(pip_path), "install", "--upgrade", "pip"],
                check=True,
                capture_output=True,
                text=True,
            )

            # Install packages
            requirements_content = env.get_requirements_file()
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".txt", delete=False
            ) as f:
                f.write(requirements_content)
                req_file = f.name

            try:
                result = subprocess.run(
                    [str(pip_path), "install", "-r", req_file],
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=600,
                )

                logger.info(f"Successfully set up environment {env_id}")
                return True, f"Environment setup completed: {result.stdout}"

            finally:
                os.unlink(req_file)

        except subprocess.CalledProcessError as e:
            error_msg = f"Failed to setup environment: {e.stderr}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Error setting up environment: {e}"
            logger.error(error_msg)
            return False, error_msg

    def execute_in_environment(
        self, env_id: str, code: str, timeout: int = 300
    ) -> Tuple[bool, Dict[str, Any]]:
        """Execute code in the specified environment."""
        env = self.get_environment(env_id)
        if not env:
            return False, {"error": "Environment not found"}

        # Check if environment is set up
        python_path = env.env_path / "bin" / "python"
        if not python_path.exists():  # Windows
            python_path = env.env_path / "Scripts" / "python.exe"

        if not python_path.exists():
            # Set up environment first
            success, message = self.setup_environment(env_id)
            if not success:
                return False, {"error": f"Environment setup failed: {message}"}

        try:
            # Create temporary script file
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
                f.write(code)
                script_path = f.name

            try:
                # Execute code
                result = subprocess.run(
                    [str(python_path), script_path],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    cwd=env.env_path,
                )

                # Update last used timestamp
                env.last_used = timezone.now()
                self._save_environments()

                return True, {
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "return_code": result.returncode,
                    "execution_time": timeout,  # Could track actual time
                }

            finally:
                os.unlink(script_path)

        except subprocess.TimeoutExpired:
            return False, {"error": "Code execution timed out"}
        except Exception as e:
            return False, {"error": f"Execution error: {e}"}

    def get_environment_info(self, env_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about an environment."""
        env = self.get_environment(env_id)
        if not env:
            return None

        # Check if environment is set up
        python_path = env.env_path / "bin" / "python"
        if not python_path.exists():  # Windows
            python_path = env.env_path / "Scripts" / "python.exe"

        is_setup = python_path.exists()

        info = env.to_dict()
        info.update(
            {
                "is_setup": is_setup,
                "path": str(env.env_path),
                "python_executable": str(python_path) if is_setup else None,
                "package_count": len(env.base_packages) + len(env.requirements),
            }
        )

        # Get installed packages if environment is set up
        if is_setup:
            try:
                result = subprocess.run(
                    [str(python_path), "-m", "pip", "list", "--format=json"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

                if result.returncode == 0:
                    installed_packages = json.loads(result.stdout)
                    info["installed_packages"] = installed_packages

            except Exception as e:
                logger.warning(
                    f"Could not get installed packages for env {env_id}: {e}"
                )

        return info

    def clone_environment(
        self, source_env_id: str, new_name: str
    ) -> Optional[Environment]:
        """Clone an existing environment."""
        source_env = self.get_environment(source_env_id)
        if not source_env:
            return None

        # Create new environment with same requirements
        requirements = [str(req) for req in source_env.requirements]
        new_env = self.create_environment(new_name, requirements)
        new_env.python_version = source_env.python_version

        self._save_environments()
        return new_env
