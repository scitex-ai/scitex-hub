#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_hub/__init__.py

"""
SciTeX Hub - CLI tools and APIs for SciTeX deployment and management.

Usage:
    pip install scitex-hub
    scitex-hub --help

Python API:
    >>> import scitex_hub
    >>> client = scitex_hub.CloudClient()
    >>> client.scholar_search("neural networks")
    >>> client.enrich_bibtex("@article{...}")

MCP Server:
    scitex-hub serve              # stdio (Claude Desktop)
    scitex-hub serve -t sse       # SSE (remote)
"""


def _get_version() -> str:
    """Read installed package version via ``importlib.metadata``.

    PEP 566 / 621 publishes the distribution version in the package
    metadata. ``importlib.metadata.version`` reads that without
    re-parsing pyproject.toml — which (a) works the same on editable
    installs and on built wheels, (b) doesn't break when pyproject.toml
    isn't shipped (wheel / sdist install), and (c) matches the rule
    PA-202 §2 (version-not-from-metadata) the ecosystem audit enforces.

    Falls back to ``"unknown"`` when the dist isn't installed (e.g.
    running directly from a checkout without ``pip install -e .``),
    so import never raises.
    """
    from importlib.metadata import PackageNotFoundError, version

    try:
        return version("scitex-hub")
    except PackageNotFoundError:
        return "unknown"


__version__ = _get_version()
__author__ = "SciTeX Team"

from . import account as account
from ._api import CloudClient as CloudClient
from ._config._environments import Environment as Environment
from ._config._environments import get_environment as get_environment
from ._utils._docker import DockerManager as DockerManager


def get_version() -> str:
    """Get scitex-hub version."""
    return __version__


def get_context(page: str = "", **kw) -> dict:
    """Get web app context: username, page, skills, available actions.

    Convenience wrapper over :class:`CloudClient.get_context`.

    Parameters
    ----------
    page : str, optional
        Page name or URL fragment to query context for. ``""`` means the
        current page.
    **kw
        Forwarded to :class:`CloudClient` (e.g. base URL, auth credentials).

    Returns
    -------
    dict
        Context dict (``username``, ``page``, ``actions``, ...).
    """
    return CloudClient(**kw).get_context(page)


def eval_js(code: str, timeout: int = 10, **kw) -> dict:
    """Evaluate JavaScript in the user's connected browser.

    Convenience wrapper over :class:`CloudClient.eval_js`.

    Parameters
    ----------
    code : str
        JavaScript code to evaluate.
    timeout : int, optional
        Seconds to wait for the result (default ``10``).
    **kw
        Forwarded to :class:`CloudClient`.

    Returns
    -------
    dict
        Result of the JavaScript evaluation.
    """
    return CloudClient(**kw).eval_js(code, timeout)


def ui_action(steps: list, delay_ms: int = 900, **kw) -> dict:
    """Drive browser UI: navigate, highlight, click, fill, scroll.

    Convenience wrapper over :class:`CloudClient.ui_action`.

    Parameters
    ----------
    steps : list
        List of action-step dicts; each describes one browser action.
    delay_ms : int, optional
        Milliseconds to wait between steps (default ``900``).
    **kw
        Forwarded to :class:`CloudClient`.

    Returns
    -------
    dict
        Result summary.
    """
    return CloudClient(**kw).ui_action(steps, delay_ms)


def health_check(endpoint: str | None = None) -> dict:
    """Check scitex-hub service health.

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
        "package": "scitex-hub",
    }


__all__ = [
    "__version__",
    "account",
    "get_version",
    "health_check",
    "get_context",
    "eval_js",
    "ui_action",
    "CloudClient",
    "Environment",
    "get_environment",
    "DockerManager",
]

# EOF
