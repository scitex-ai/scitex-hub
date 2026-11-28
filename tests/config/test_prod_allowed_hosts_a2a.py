#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/config/test_prod_allowed_hosts_a2a.py
"""Production accepts the A2A subdomain it routes to Django.

``nginx_prod.conf`` sends ``a2a.<site domain>`` to Django, but
``ALLOWED_HOSTS`` came only from the host's .env, which listed the apex. On
2026-11-27 every request to https://a2a.scitex.ai/ was a 400 DisallowedHost
and the admin rail mailed the operator about it. ``settings_prod`` now derives
the A2A host from ``SCITEX_HUB_SITE_URL``.

Composed in a subprocess, the same way tests/config/
test_logging_wiring_per_environment.py does it: a deployed process imports
exactly one settings module.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from tests.config.test_logging_wiring_per_environment import REQUIRED_CONFIG

REPO_ROOT = Path(__file__).resolve().parents[2]

# The value production's .env carried when the error was reported.
LIVE_ALLOWED_HOSTS = "scitex.ai,www.scitex.ai,web,nginx,localhost"

_PROBE = """
import importlib, json, sys
module = importlib.import_module("config.settings.settings_prod")
with open(sys.argv[1], "w", encoding="utf-8") as fh:
    json.dump(list(module.ALLOWED_HOSTS), fh)
"""


def composed_allowed_hosts(site_url: str | None) -> list[str]:
    environment = dict(os.environ)
    environment.update(REQUIRED_CONFIG["settings_prod"])
    environment["SCITEX_HUB_ALLOWED_HOSTS"] = LIVE_ALLOWED_HOSTS
    environment.pop("SCITEX_HUB_SITE_URL", None)
    environment.pop("SITE_URL", None)
    if site_url is not None:
        environment["SCITEX_HUB_SITE_URL"] = site_url
    workdir = Path(tempfile.mkdtemp(prefix="hub-allowed-hosts-"))
    environment["SCITEX_HUB_LOG_DIR"] = str(workdir)
    environment["PYTHONPATH"] = os.pathsep.join(
        [str(REPO_ROOT), environment.get("PYTHONPATH", "")]
    ).rstrip(os.pathsep)
    out_path = workdir / "allowed-hosts.json"
    completed = subprocess.run(
        [sys.executable, "-c", _PROBE, str(out_path)],
        cwd=str(REPO_ROOT),
        env=environment,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0 or not out_path.exists():
        raise AssertionError(
            f"settings_prod did not compose.\n--- stderr ---\n{completed.stderr}"
        )
    return json.loads(out_path.read_text(encoding="utf-8"))


def test_prod_allows_the_a2a_subdomain_of_the_site() -> None:
    # Arrange
    site_url = "https://scitex.ai"
    # Act
    hosts = composed_allowed_hosts(site_url)
    # Assert
    assert "a2a.scitex.ai" in hosts


def test_prod_derives_a2a_from_the_apex_of_a_www_site_url() -> None:
    # Arrange
    site_url = "https://www.example.org"
    # Act
    hosts = composed_allowed_hosts(site_url)
    # Assert
    assert "a2a.example.org" in hosts


def test_prod_adds_no_a2a_host_without_a_site_url() -> None:
    # Arrange
    site_url = None
    # Act
    hosts = composed_allowed_hosts(site_url)
    # Assert
    assert [h for h in hosts if h.startswith("a2a.")] == []
