#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for apps/console_app/environment_manager.py"""

import pytest

# from apps.console_app.environment_manager import ...


class TestPlaceholder:
    """Placeholder test class - replace with actual tests."""

    def test_placeholder(self):
        """Placeholder test - implement actual tests."""
        pytest.skip("Not implemented yet")

if __name__ == "__main__":
    import os

    import pytest

    pytest.main([os.path.abspath(__file__)])

# --------------------------------------------------------------------------------
# Start of Source Code from: apps/console_app/environment_manager.py
# --------------------------------------------------------------------------------
# #!/usr/bin/env python3
# """
# Environment Management for SciTeX-Code
# Provides reproducible Python environments with package management.
# """
# 
# import os
# import json
# import subprocess
# import tempfile
# import venv
# import uuid
# from pathlib import Path
# from typing import Dict, List, Optional, Tuple, Any
# import logging
# 
# from django.conf import settings
# from django.utils import timezone
# from django.contrib.auth.models import User
# 
# 
# logger = logging.getLogger(__name__)
# 
# 
# class EnvironmentError(Exception):
#     """Raised when environment operations fail."""
# 
#     pass
# 
# 
# class PackageRequirement:
#     """Represents a Python package requirement."""
# 
#     def __init__(
#         self,
#         name: str,
#         version: Optional[str] = None,
#         source: str = "pypi",
#         extras: Optional[List[str]] = None,
#     ):
#         self.name = name
#         self.version = version
#         self.source = source
#         self.extras = extras or []
# 
#     def __str__(self):
#         """Return pip-compatible requirement string."""
#         req = self.name
#         if self.extras:
#             req += f"[{','.join(self.extras)}]"
#         if self.version:
#             req += f"=={self.version}"
#         return req
# 
#     @classmethod
#     def from_string(cls, req_string: str):
#         """Parse requirement from string like 'numpy==1.21.0' or 'scipy[linalg]'."""
#         # Basic parsing - can be enhanced for more complex requirements
#         extras = []
#         name = req_string
#         version = None
# 
#         # Extract extras
#         if "[" in req_string:
#             name, extras_part = req_string.split("[", 1)
#             extras = extras_part.rstrip("]").split(",")
# 
#         # Extract version
#         if "==" in name:
#             name, version = name.split("==", 1)
#         elif ">=" in name:
#             name, version = name.split(">=", 1)
#             version = f">={version}"
#         elif "<=" in name:
#             name, version = name.split("<=", 1)
#             version = f"<={version}"
# 
#         return cls(name.strip(), version, extras=extras)
# 
# 
# class Environment:
#     """Represents a Python execution environment."""
# 
#     def __init__(self, env_id: str, user: User, name: str = ""):
#         self.env_id = env_id
#         self.user = user
#         self.name = name or f"env_{env_id[:8]}"
#         self.base_path = Path(settings.MEDIA_ROOT) / "environments" / str(user.id)
#         self.env_path = self.base_path / env_id
#         self.requirements: List[PackageRequirement] = []
#         self.python_version = "3.11"
#         self.created_at = timezone.now()
#         self.last_used = timezone.now()
# 
#         # Standard scientific packages
#         self.base_packages = [
#             PackageRequirement("numpy", "1.24.3"),
#             PackageRequirement("pandas", "2.0.3"),
#             PackageRequirement("matplotlib", "3.7.1"),
#             PackageRequirement("seaborn", "0.12.2"),
#             PackageRequirement("scipy", "1.10.1"),
#             PackageRequirement("scikit-learn", "1.3.0"),
#             PackageRequirement("jupyter", "1.0.0"),
#             PackageRequirement("ipykernel", "6.25.0"),
#         ]
# 
#     def add_requirement(self, requirement: PackageRequirement):
#         """Add a package requirement to the environment."""
#         # Remove existing requirement with same name
#         self.requirements = [r for r in self.requirements if r.name != requirement.name]
#         self.requirements.append(requirement)
# 
#     def get_requirements_file(self) -> str:
#         """Generate requirements.txt content."""
#         all_reqs = self.base_packages + self.requirements
#         return "\n".join(str(req) for req in all_reqs)
# 
#     def to_dict(self) -> Dict[str, Any]:
#         """Convert environment to dictionary for serialization."""
#         return {
#             "env_id": self.env_id,
#             "name": self.name,
#             "python_version": self.python_version,
#             "requirements": [str(req) for req in self.requirements],
#             "created_at": self.created_at.isoformat(),
#             "last_used": self.last_used.isoformat(),
#         }
# 
#     @classmethod
#     def from_dict(cls, data: Dict[str, Any], user: User):
#         """Create environment from dictionary."""
#         env = cls(data["env_id"], user, data["name"])
#         env.python_version = data.get("python_version", "3.11")
#         env.requirements = [
#             PackageRequirement.from_string(req) for req in data.get("requirements", [])
#         ]
#         env.created_at = timezone.datetime.fromisoformat(data["created_at"])
#         env.last_used = timezone.datetime.fromisoformat(data["last_used"])
#         return env
# 
# 
# class EnvironmentManager:
#     """Manages Python execution environments."""
# 
#     def __init__(self, user: User):
#         self.user = user
#         self.base_path = Path(settings.MEDIA_ROOT) / "environments" / str(user.id)
#         self.base_path.mkdir(parents=True, exist_ok=True)
#         self.metadata_file = self.base_path / "environments.json"
#         self._environments: Dict[str, Environment] = {}
#         self._load_environments()
# 
#     def _load_environments(self):
#         """Load existing environments from metadata file."""
#         if self.metadata_file.exists():
#             try:
#                 with open(self.metadata_file) as f:
#                     data = json.load(f)
# 
#                 for env_data in data.get("environments", []):
#                     env = Environment.from_dict(env_data, self.user)
#                     self._environments[env.env_id] = env
# 
#             except Exception as e:
#                 logger.error(
#                     f"Error loading environments for user {self.user.username}: {e}"
#                 )
# 
#     def _save_environments(self):
#         """Save environments metadata to file."""
#         try:
#             data = {
#                 "environments": [env.to_dict() for env in self._environments.values()],
#                 "updated_at": timezone.now().isoformat(),
#             }
# 
#             with open(self.metadata_file, "w") as f:
#                 json.dump(data, f, indent=2)
# 
#         except Exception as e:
#             logger.error(
#                 f"Error saving environments for user {self.user.username}: {e}"
#             )
# 
#     def create_environment(
#         self, name: str, requirements: Optional[List[str]] = None
#     ) -> Environment:
#         """Create a new Python environment."""
#         env_id = str(uuid.uuid4())
#         env = Environment(env_id, self.user, name)
# 
#         # Add custom requirements
#         if requirements:
#             for req_str in requirements:
#                 try:
#                     req = PackageRequirement.from_string(req_str)
#                     env.add_requirement(req)
#                 except Exception as e:
#                     logger.warning(f"Invalid requirement '{req_str}': {e}")
# 
#         self._environments[env_id] = env
#         self._save_environments()
# 
#         logger.info(
#             f"Created environment '{name}' ({env_id}) for user {self.user.username}"
#         )
#         return env
# 
#     def get_environment(self, env_id: str) -> Optional[Environment]:
#         """Get environment by ID."""
#         return self._environments.get(env_id)
# 
#     def list_environments(self) -> List[Environment]:
#         """List all user environments."""
#         return list(self._environments.values())
# 
#     def delete_environment(self, env_id: str) -> bool:
#         """Delete an environment."""
#         if env_id not in self._environments:
#             return False
# 
#         env = self._environments[env_id]
# 
#         # Remove environment directory if it exists
#         if env.env_path.exists():
#             import shutil
# 
#             try:
#                 shutil.rmtree(env.env_path)
#             except Exception as e:
#                 logger.error(
#                     f"Error removing environment directory {env.env_path}: {e}"
#                 )
# 
#         # Remove from memory and save
#         del self._environments[env_id]
#         self._save_environments()
# 
#         logger.info(f"Deleted environment {env_id} for user {self.user.username}")
#         return True
# 
#     def setup_environment(self, env_id: str) -> Tuple[bool, str]:
#         """Set up the Python virtual environment with packages."""
#         env = self.get_environment(env_id)
#         if not env:
#             return False, "Environment not found"
# 
#         try:
#             # Create virtual environment
#             venv.create(env.env_path, with_pip=True, clear=True)
# 
#             # Get pip executable path
#             pip_path = env.env_path / "bin" / "pip"
#             if not pip_path.exists():  # Windows
#                 pip_path = env.env_path / "Scripts" / "pip.exe"
# 
#             # Upgrade pip
#             subprocess.run(
#                 [str(pip_path), "install", "--upgrade", "pip"],
#                 check=True,
#                 capture_output=True,
#                 text=True,
#             )
# 
#             # Install packages
#             requirements_content = env.get_requirements_file()
#             with tempfile.NamedTemporaryFile(
#                 mode="w", suffix=".txt", delete=False
#             ) as f:
#                 f.write(requirements_content)
#                 req_file = f.name
# 
#             try:
#                 result = subprocess.run(
#                     [str(pip_path), "install", "-r", req_file],
#                     check=True,
#                     capture_output=True,
#                     text=True,
#                     timeout=600,
#                 )
# 
#                 logger.info(f"Successfully set up environment {env_id}")
#                 return True, f"Environment setup completed: {result.stdout}"
# 
#             finally:
#                 os.unlink(req_file)
# 
#         except subprocess.CalledProcessError as e:
#             error_msg = f"Failed to setup environment: {e.stderr}"
#             logger.error(error_msg)
#             return False, error_msg
#         except Exception as e:
#             error_msg = f"Error setting up environment: {e}"
#             logger.error(error_msg)
#             return False, error_msg
# 
#     def execute_in_environment(
#         self, env_id: str, console: str, timeout: int = 300
#     ) -> Tuple[bool, Dict[str, Any]]:
#         """Execute code in the specified environment."""
#         env = self.get_environment(env_id)
#         if not env:
#             return False, {"error": "Environment not found"}
# 
#         # Check if environment is set up
#         python_path = env.env_path / "bin" / "python"
#         if not python_path.exists():  # Windows
#             python_path = env.env_path / "Scripts" / "python.exe"
# 
#         if not python_path.exists():
#             # Set up environment first
#             success, message = self.setup_environment(env_id)
#             if not success:
#                 return False, {"error": f"Environment setup failed: {message}"}
# 
#         try:
#             # Create temporary script file
#             with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
#                 f.write(code)
#                 script_path = f.name
# 
#             try:
#                 # Execute code
#                 result = subprocess.run(
#                     [str(python_path), script_path],
#                     capture_output=True,
#                     text=True,
#                     timeout=timeout,
#                     cwd=env.env_path,
#                 )
# 
#                 # Update last used timestamp
#                 env.last_used = timezone.now()
#                 self._save_environments()
# 
#                 return True, {
#                     "stdout": result.stdout,
#                     "stderr": result.stderr,
#                     "return_code": result.returncode,
#                     "execution_time": timeout,  # Could track actual time
#                 }
# 
#             finally:
#                 os.unlink(script_path)
# 
#         except subprocess.TimeoutExpired:
#             return False, {"error": "Code execution timed out"}
#         except Exception as e:
#             return False, {"error": f"Execution error: {e}"}
# 
#     def get_environment_info(self, env_id: str) -> Optional[Dict[str, Any]]:
#         """Get detailed information about an environment."""
#         env = self.get_environment(env_id)
#         if not env:
#             return None
# 
#         # Check if environment is set up
#         python_path = env.env_path / "bin" / "python"
#         if not python_path.exists():  # Windows
#             python_path = env.env_path / "Scripts" / "python.exe"
# 
#         is_setup = python_path.exists()
# 
#         info = env.to_dict()
#         info.update(
#             {
#                 "is_setup": is_setup,
#                 "path": str(env.env_path),
#                 "python_executable": str(python_path) if is_setup else None,
#                 "package_count": len(env.base_packages) + len(env.requirements),
#             }
#         )
# 
#         # Get installed packages if environment is set up
#         if is_setup:
#             try:
#                 result = subprocess.run(
#                     [str(python_path), "-m", "pip", "list", "--format=json"],
#                     capture_output=True,
#                     text=True,
#                     timeout=30,
#                 )
# 
#                 if result.returncode == 0:
#                     installed_packages = json.loads(result.stdout)
#                     info["installed_packages"] = installed_packages
# 
#             except Exception as e:
#                 logger.warning(
#                     f"Could not get installed packages for env {env_id}: {e}"
#                 )
# 
#         return info
# 
#     def clone_environment(
#         self, source_env_id: str, new_name: str
#     ) -> Optional[Environment]:
#         """Clone an existing environment."""
#         source_env = self.get_environment(source_env_id)
#         if not source_env:
#             return None
# 
#         # Create new environment with same requirements
#         requirements = [str(req) for req in source_env.requirements]
#         new_env = self.create_environment(new_name, requirements)
#         new_env.python_version = source_env.python_version
# 
#         self._save_environments()
#         return new_env
# 
# 
# class WorkflowManager:
#     """Manages reproducible research workflows."""
# 
#     def __init__(self, user: User):
#         self.user = user
#         self.env_manager = EnvironmentManager(user)
# 
#     def create_workflow(
#         self, name: str, description: str, steps: List[Dict[str, Any]]
#     ) -> Dict[str, Any]:
#         """Create a reproducible research workflow."""
#         workflow_id = str(uuid.uuid4())
# 
#         workflow = {
#             "id": workflow_id,
#             "name": name,
#             "description": description,
#             "created_by": self.user.username,
#             "created_at": timezone.now().isoformat(),
#             "steps": steps,
#             "status": "draft",
#         }
# 
#         # Save workflow
#         workflows_dir = Path(settings.MEDIA_ROOT) / "workflows" / str(self.user.id)
#         workflows_dir.mkdir(parents=True, exist_ok=True)
# 
#         workflow_file = workflows_dir / f"{workflow_id}.json"
#         with open(workflow_file, "w") as f:
#             json.dump(workflow, f, indent=2)
# 
#         logger.info(
#             f"Created workflow '{name}' ({workflow_id}) for user {self.user.username}"
#         )
#         return workflow
# 
#     def execute_workflow(self, workflow_id: str) -> Tuple[bool, List[Dict[str, Any]]]:
#         """Execute a research workflow."""
#         workflows_dir = Path(settings.MEDIA_ROOT) / "workflows" / str(self.user.id)
#         workflow_file = workflows_dir / f"{workflow_id}.json"
# 
#         if not workflow_file.exists():
#             return False, [{"error": "Workflow not found"}]
# 
#         try:
#             with open(workflow_file) as f:
#                 workflow = json.load(f)
# 
#             results = []
# 
#             for i, step in enumerate(workflow["steps"]):
#                 step_type = step.get("type", "code")
# 
#                 if step_type == "code":
#                     # Execute code step
#                     env_id = step.get("environment_id")
#                     code = step.get("code", "")
# 
#                     if env_id:
#                         success, result = self.env_manager.execute_in_environment(
#                             env_id, code, timeout=step.get("timeout", 300)
#                         )
#                     else:
#                         # Use default environment
#                         success, result = self._execute_default(code)
# 
#                     results.append(
#                         {
#                             "step": i + 1,
#                             "type": step_type,
#                             "success": success,
#                             "result": result,
#                             "timestamp": timezone.now().isoformat(),
#                         }
#                     )
# 
#                 elif step_type == "environment_setup":
#                     # Set up environment step
#                     env_name = step.get(
#                         "environment_name", f"workflow_{workflow_id}_env"
#                     )
#                     requirements = step.get("requirements", [])
# 
#                     env = self.env_manager.create_environment(env_name, requirements)
#                     success, message = self.env_manager.setup_environment(env.env_id)
# 
#                     results.append(
#                         {
#                             "step": i + 1,
#                             "type": step_type,
#                             "success": success,
#                             "result": {
#                                 "message": message,
#                                 "environment_id": env.env_id,
#                             },
#                             "timestamp": timezone.now().isoformat(),
#                         }
#                     )
# 
#                 # Stop execution if step failed and marked as critical
#                 if not results[-1]["success"] and step.get("critical", True):
#                     break
# 
#             return True, results
# 
#         except Exception as e:
#             logger.error(f"Error executing workflow {workflow_id}: {e}")
#             return False, [{"error": str(e)}]
# 
#     def _execute_default(self, console: str) -> Tuple[bool, Dict[str, Any]]:
#         """Execute code in default environment."""
#         # This is a fallback - in production you'd want a default environment
#         try:
#             with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
#                 f.write(code)
#                 script_path = f.name
# 
#             try:
#                 result = subprocess.run(
#                     ["python3", script_path],
#                     capture_output=True,
#                     text=True,
#                     timeout=300,
#                 )
# 
#                 return True, {
#                     "stdout": result.stdout,
#                     "stderr": result.stderr,
#                     "return_code": result.returncode,
#                 }
# 
#             finally:
#                 os.unlink(script_path)
# 
#         except Exception as e:
#             return False, {"error": str(e)}

# --------------------------------------------------------------------------------
# End of Source Code from: apps/console_app/environment_manager.py
# --------------------------------------------------------------------------------
