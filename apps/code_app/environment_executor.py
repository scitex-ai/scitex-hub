#!/usr/bin/env python3
"""
Environment Executor - Code execution in Python environments.
"""

import json
import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


def get_python_path(env_path: Path) -> Path:
    """Get Python executable path for environment (cross-platform)."""
    python_path = env_path / "bin" / "python"
    if not python_path.exists():
        python_path = env_path / "Scripts" / "python.exe"
    return python_path


def execute_code(
    env_path: Path, code: str, timeout: int = 300
) -> Tuple[bool, Dict[str, Any]]:
    """Execute code in an environment."""
    python_path = get_python_path(env_path)

    if not python_path.exists():
        return False, {"error": "Python executable not found"}

    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            script_path = f.name

        try:
            result = subprocess.run(
                [str(python_path), script_path],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=env_path,
            )

            return True, {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode,
                "execution_time": timeout,
            }

        finally:
            os.unlink(script_path)

    except subprocess.TimeoutExpired:
        return False, {"error": "Code execution timed out"}
    except Exception as e:
        return False, {"error": f"Execution error: {e}"}


def get_installed_packages(env_path: Path) -> Optional[list]:
    """Get list of installed packages in environment."""
    python_path = get_python_path(env_path)

    if not python_path.exists():
        return None

    try:
        result = subprocess.run(
            [str(python_path), "-m", "pip", "list", "--format=json"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode == 0:
            return json.loads(result.stdout)

    except Exception as e:
        logger.warning(f"Could not get installed packages: {e}")

    return None
