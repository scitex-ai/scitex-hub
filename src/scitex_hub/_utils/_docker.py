#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_hub/utils/docker.py

"""Docker management utilities for SciTeX Cloud."""

import subprocess
from pathlib import Path
from typing import List, Optional

from .._config._environments import Environment, get_environment


class DockerManager:
    """Manage Docker containers for SciTeX Cloud."""

    def __init__(
        self, env: Optional[Environment] = None, project_root: Optional[Path] = None
    ):
        self.env = env or get_environment()
        self.project_root = project_root or self._find_project_root()

    def _find_project_root(self) -> Path:
        """Find project root by looking for pyproject.toml."""
        current = Path.cwd()
        for parent in [current] + list(current.parents):
            if (parent / "pyproject.toml").exists():
                return parent
        return current

    def _run_compose(
        self, args: List[str], capture: bool = False
    ) -> subprocess.CompletedProcess:
        """Run docker-compose command."""
        compose_file = self.project_root / self.env.compose_path
        env_file = self.project_root / self.env.env_path

        cmd = ["docker", "compose", "-f", str(compose_file)]
        if env_file.exists():
            cmd.extend(["--env-file", str(env_file)])
        cmd.extend(args)

        kwargs = {"cwd": self.project_root}
        if capture:
            kwargs["capture_output"] = True
            kwargs["text"] = True

        return subprocess.run(cmd, **kwargs)

    def build(self, no_cache: bool = False) -> int:
        """Build Docker containers."""
        args = ["build"]
        if no_cache:
            args.append("--no-cache")
        result = self._run_compose(args)
        return result.returncode

    def up(self, detach: bool = True) -> int:
        """Start Docker containers."""
        args = ["up"]
        if detach:
            args.append("-d")
        result = self._run_compose(args)
        return result.returncode

    def down(self, volumes: bool = False) -> int:
        """Stop Docker containers."""
        args = ["down"]
        if volumes:
            args.append("-v")
        result = self._run_compose(args)
        return result.returncode

    def restart(self) -> int:
        """Restart Docker containers."""
        result = self._run_compose(["restart"])
        return result.returncode

    def logs(
        self,
        follow: bool = False,
        tail: Optional[int] = None,
        service: Optional[str] = None,
    ) -> int:
        """Show container logs."""
        args = ["logs"]
        if follow:
            args.append("-f")
        if tail:
            args.extend(["--tail", str(tail)])
        if service:
            args.append(service)
        result = self._run_compose(args)
        return result.returncode

    def ps(self) -> int:
        """Show container status."""
        result = self._run_compose(["ps"])
        return result.returncode

    def status(self) -> dict:
        """Get detailed container status."""
        result = self._run_compose(["ps", "--format", "json"], capture=True)
        return {
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }


# EOF
