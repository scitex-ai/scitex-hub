#!/usr/bin/env python3
"""
Workflow Manager - Manages reproducible research workflows.
"""

import json
import logging
import os
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Any, Dict, List, Tuple

from django.conf import settings
from django.contrib.auth.models import User
from django.utils import timezone

logger = logging.getLogger(__name__)


class WorkflowManager:
    """Manages reproducible research workflows."""

    def __init__(self, user: User):
        from .environment_manager import EnvironmentManager

        self.user = user
        self.env_manager = EnvironmentManager(user)

    def create_workflow(
        self, name: str, description: str, steps: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Create a reproducible research workflow."""
        workflow_id = str(uuid.uuid4())

        workflow = {
            "id": workflow_id,
            "name": name,
            "description": description,
            "created_by": self.user.username,
            "created_at": timezone.now().isoformat(),
            "steps": steps,
            "status": "draft",
        }

        # Save workflow
        workflows_dir = Path(settings.MEDIA_ROOT) / "workflows" / str(self.user.id)
        workflows_dir.mkdir(parents=True, exist_ok=True)

        workflow_file = workflows_dir / f"{workflow_id}.json"
        with open(workflow_file, "w") as f:
            json.dump(workflow, f, indent=2)

        logger.info(
            f"Created workflow '{name}' ({workflow_id}) for user {self.user.username}"
        )
        return workflow

    def execute_workflow(self, workflow_id: str) -> Tuple[bool, List[Dict[str, Any]]]:
        """Execute a research workflow."""
        workflows_dir = Path(settings.MEDIA_ROOT) / "workflows" / str(self.user.id)
        workflow_file = workflows_dir / f"{workflow_id}.json"

        if not workflow_file.exists():
            return False, [{"error": "Workflow not found"}]

        try:
            with open(workflow_file) as f:
                workflow = json.load(f)

            results = []

            for i, step in enumerate(workflow["steps"]):
                step_type = step.get("type", "code")

                if step_type == "code":
                    env_id = step.get("environment_id")
                    code = step.get("code", "")

                    if env_id:
                        success, result = self.env_manager.execute_in_environment(
                            env_id, code, timeout=step.get("timeout", 300)
                        )
                    else:
                        success, result = self._execute_default(code)

                    results.append(
                        {
                            "step": i + 1,
                            "type": step_type,
                            "success": success,
                            "result": result,
                            "timestamp": timezone.now().isoformat(),
                        }
                    )

                elif step_type == "environment_setup":
                    env_name = step.get(
                        "environment_name", f"workflow_{workflow_id}_env"
                    )
                    requirements = step.get("requirements", [])

                    env = self.env_manager.create_environment(env_name, requirements)
                    success, message = self.env_manager.setup_environment(env.env_id)

                    results.append(
                        {
                            "step": i + 1,
                            "type": step_type,
                            "success": success,
                            "result": {
                                "message": message,
                                "environment_id": env.env_id,
                            },
                            "timestamp": timezone.now().isoformat(),
                        }
                    )

                # Stop execution if step failed and marked as critical
                if not results[-1]["success"] and step.get("critical", True):
                    break

            return True, results

        except Exception as e:
            logger.error(f"Error executing workflow {workflow_id}: {e}")
            return False, [{"error": str(e)}]

    def _execute_default(self, console: str) -> Tuple[bool, Dict[str, Any]]:
        """Execute code in default environment."""
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
                f.write(code)
                script_path = f.name

            try:
                result = subprocess.run(
                    ["python3", script_path],
                    capture_output=True,
                    text=True,
                    timeout=300,
                )

                return True, {
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "return_code": result.returncode,
                }

            finally:
                os.unlink(script_path)

        except Exception as e:
            return False, {"error": str(e)}
