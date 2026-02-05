#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_cloud/config/environments.py

"""Environment configuration for SciTeX Cloud deployments."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class Environment:
    """Deployment environment configuration."""

    name: str
    docker_compose_file: str
    env_file: str
    host: str
    port: int
    description: str

    @property
    def env_path(self) -> Path:
        """Get full path to .env file."""
        return Path("SECRET") / self.env_file

    @property
    def compose_path(self) -> Path:
        """Get full path to docker-compose file."""
        return Path("deployment/docker") / self.docker_compose_file


ENVIRONMENTS = {
    "dev": Environment(
        name="dev",
        docker_compose_file="docker_dev/docker-compose.yml",
        env_file=".env.dev",
        host="127.0.0.1",
        port=8000,
        description="Development environment (local)",
    ),
    "prod": Environment(
        name="prod",
        docker_compose_file="docker_prod/docker-compose.yml",
        env_file=".env.prod",
        host="0.0.0.0",
        port=8000,
        description="Production environment",
    ),
}


def get_environment(name: Optional[str] = None) -> Environment:
    """Get environment configuration by name or auto-detect."""
    if name:
        if name not in ENVIRONMENTS:
            raise ValueError(
                f"Unknown environment: {name}. Available: {list(ENVIRONMENTS.keys())}"
            )
        return ENVIRONMENTS[name]

    # Auto-detect from SCITEX_CLOUD_ENV or default to dev
    env_name = os.environ.get("SCITEX_CLOUD_ENV", "dev")
    return ENVIRONMENTS.get(env_name, ENVIRONMENTS["dev"])


# EOF
