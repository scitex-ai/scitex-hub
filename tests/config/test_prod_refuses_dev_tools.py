#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Production settings never mount the /dev/ developer toolbox.

``settings_prod`` forces ``DEV_TOOLS_ENABLED`` off and refuses to start when
the environment asks for it. Composed in a subprocess, like
tests/config/test_prod_allowed_hosts_a2a.py: a deployed process imports
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

_PROBE = """
import importlib, json, sys
module = importlib.import_module("config.settings.settings_prod")
with open(sys.argv[1], "w", encoding="utf-8") as fh:
    json.dump({"dev_tools": module.DEV_TOOLS_ENABLED}, fh)
"""


def compose_prod(dev_tools_env: str | None) -> subprocess.CompletedProcess:
    environment = dict(os.environ)
    environment.update(REQUIRED_CONFIG["settings_prod"])
    environment.pop("SCITEX_HUB_DEV_TOOLS_ENABLED", None)
    if dev_tools_env is not None:
        environment["SCITEX_HUB_DEV_TOOLS_ENABLED"] = dev_tools_env
    workdir = Path(tempfile.mkdtemp(prefix="hub-prod-dev-tools-"))
    environment["SCITEX_HUB_LOG_DIR"] = str(workdir)
    environment["PYTHONPATH"] = os.pathsep.join(
        [str(REPO_ROOT), environment.get("PYTHONPATH", "")]
    ).rstrip(os.pathsep)
    out_path = workdir / "dev-tools.json"
    completed = subprocess.run(
        [sys.executable, "-c", _PROBE, str(out_path)],
        cwd=str(REPO_ROOT),
        env=environment,
        capture_output=True,
        text=True,
    )
    completed.out_path = out_path
    return completed


def test_prod_composes_with_dev_tools_off() -> None:
    # Arrange
    completed = compose_prod(None)
    # Act
    composed = json.loads(completed.out_path.read_text(encoding="utf-8"))
    # Assert
    assert composed == {"dev_tools": False}


def test_prod_refuses_to_start_when_dev_tools_are_requested() -> None:
    # Arrange
    requested = "true"
    # Act
    completed = compose_prod(requested)
    # Assert
    assert "SCITEX_HUB_DEV_TOOLS_ENABLED must not be set" in completed.stderr
