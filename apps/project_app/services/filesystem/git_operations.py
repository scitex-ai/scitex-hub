"""
Git operations for project filesystem.

This module handles Git-related operations like cloning repositories.
"""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Tuple, Optional
from ...models import Project
from .paths import get_project_root_path


def clone_from_git(
    user, project: Project, git_url: str, use_ssh: bool = True
) -> Tuple[bool, Optional[str]]:
    """
    Clone a Git repository into the project directory.

    Args:
        user: User instance
        project: Project instance
        git_url: Git repository URL (works with GitHub, GitLab, Bitbucket, etc.)
        use_ssh: If True and SSH key exists, use SSH for cloning

    Returns:
        Tuple of (success, error_message)
    """
    try:
        project_path = get_project_root_path(user, project)
        if not project_path or not project_path.exists():
            return False, "Project directory not found"

        # Get SSH environment if available
        env = os.environ.copy()
        ssh_used = False

        if use_ssh:
            from ..ssh_manager import SSHKeyManager

            ssh_manager = SSHKeyManager(user)

            if ssh_manager.has_ssh_key():
                env = ssh_manager.get_ssh_env()
                ssh_used = True

        # Strategy: Clone to a temporary directory, then move contents
        # This avoids the "destination path already exists and is not an empty directory" error

        # Create a temporary directory for cloning
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_clone_path = Path(temp_dir) / "repo"

            # Clone the repository into the temporary directory
            result = subprocess.run(
                ["git", "clone", git_url, str(temp_clone_path)],
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
                env=env,
            )

            if result.returncode != 0:
                error_msg = result.stderr or result.stdout or "Unknown error"
                return False, error_msg

            # Remove any existing files in the project directory (created during initialization)
            for item in project_path.iterdir():
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)

            # Move all contents from temp clone to project directory
            for item in temp_clone_path.iterdir():
                dest = project_path / item.name
                if item.is_file():
                    shutil.copy2(item, dest)
                elif item.is_dir():
                    shutil.copytree(item, dest)

        # Mark SSH key as used if it was used
        if ssh_used:
            from ..ssh_manager import SSHKeyManager

            ssh_manager = SSHKeyManager(user)
            ssh_manager.mark_key_used()

        return True, None

    except subprocess.TimeoutExpired:
        return False, "Git clone operation timed out (max 5 minutes)"
    except FileNotFoundError:
        return False, "Git command not found. Please ensure Git is installed."
    except Exception as e:
        return False, str(e)


def get_script_executions(
    user, project: Project, script_name: str = None
) -> list:
    """Get execution history for scripts in the project."""
    try:
        import json

        project_path = get_project_root_path(user, project)
        if not project_path:
            return []

        scripts_path = project_path / "scripts"
        if not scripts_path.exists():
            return []

        executions = []

        # If specific script requested, only check that one
        if script_name:
            script_base = Path(script_name).stem
            script_dirs = (
                [scripts_path / script_base]
                if (scripts_path / script_base).exists()
                else []
            )
        else:
            script_dirs = [d for d in scripts_path.iterdir() if d.is_dir()]

        for script_dir in script_dirs:
            for execution_dir in script_dir.iterdir():
                if execution_dir.is_dir() and execution_dir.name.startswith(
                    "execution_"
                ):
                    # Check for status markers
                    if (execution_dir / "RUNNING").exists():
                        status = "running"
                    elif (execution_dir / "FINISHED_SUCCESS").exists():
                        status = "success"
                    elif (execution_dir / "FINISHED_ERROR").exists():
                        status = "error"
                    else:
                        status = "unknown"

                    # Try to load execution summary
                    summary_file = execution_dir / "execution_summary.json"
                    if summary_file.exists():
                        with open(summary_file, "r") as f:
                            summary = json.load(f)
                    else:
                        summary = {}

                    executions.append(
                        {
                            "script_name": script_dir.name,
                            "execution_id": execution_dir.name,
                            "status": status,
                            "path": str(execution_dir.relative_to(project_path)),
                            "timestamp": execution_dir.name.split("_", 1)[1]
                            if "_" in execution_dir.name
                            else "",
                            "summary": summary,
                        }
                    )

        # Sort by timestamp (newest first)
        executions.sort(key=lambda x: x["timestamp"], reverse=True)
        return executions
    except Exception as e:
        print(f"Error getting script executions: {e}")
        return []
