#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_cloud/__init__.py

"""
SciTeX Cloud - CLI tools and APIs for SciTeX deployment and management.

Usage:
    pip install scitex-cloud
    scitex-cloud --help

Python API:
    >>> import scitex_cloud
    >>> client = scitex_cloud.CloudClient()
    >>> client.scholar_search("neural networks")
    >>> client.enrich_bibtex("@article{...}")

MCP Server:
    scitex-cloud serve              # stdio (Claude Desktop)
    scitex-cloud serve -t sse       # SSE (remote)
"""

from __future__ import annotations


def _get_version() -> str:
    """Read version from pyproject.toml (single source of truth)."""
    from pathlib import Path

    try:
        import tomllib
    except ImportError:
        import tomli as tomllib

    pyproject = Path(__file__).resolve().parent.parent.parent / "pyproject.toml"
    if pyproject.exists():
        with open(pyproject, "rb") as f:
            data = tomllib.load(f)
            return data.get("project", {}).get("version", "unknown")
    return "unknown"


__version__ = _get_version()
__author__ = "SciTeX Team"

from .api import CloudClient
from .config.environments import Environment, get_environment
from .utils.docker import DockerManager


def get_version() -> str:
    """Get scitex-cloud version."""
    return __version__


def health_check(endpoint: str | None = None) -> dict:
    """Check scitex-cloud service health.

    Parameters
    ----------
    endpoint : str, optional
        HTTP endpoint to check. If None, returns local package info.

    Returns
    -------
    dict
        Health status with version, environment, and service status.
    """
    import json
    import urllib.request

    if endpoint:
        try:
            with urllib.request.urlopen(endpoint, timeout=5) as response:
                return json.loads(response.read().decode())
        except Exception as e:
            return {"status": "error", "error": str(e), "endpoint": endpoint}

    return {
        "status": "ok",
        "version": __version__,
        "package": "scitex-cloud",
    }


__all__ = [
    "__version__",
    "get_version",
    "health_check",
    "CloudClient",
    "Environment",
    "get_environment",
    "DockerManager",
]

# EOF
