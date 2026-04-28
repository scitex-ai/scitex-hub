#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_cloud/_config/_loader.py
"""YAML config loader for scitex-cloud CLI (spec §6b).

Provides a minimal, non-failing loader used as a last-resort fallback
for CLI values. Resolution precedence (highest first) per the SciTeX
CLI convention:

    1. CLI flag (e.g. ``--user``)
    2. Env var (``SCITEX_CLOUD_*``)
    3. Config file (this module)

Config file search order (first existing wins):

    1. explicit ``path`` argument to :func:`load_config`
    2. ``$SCITEX_CLOUD_CONFIG``
    3. ``./.scitex/scitex-cloud.yaml`` (project-local override)
    4. ``~/.scitex/scitex-cloud/config.yaml`` (user default)

If none of those resolve to a readable YAML file, an empty dict is
returned — missing config is not an error.

Schema (all keys optional)::

    workspace:
      url: https://scitex-cloud.com
      user: <username>
    gitea:
      url: https://gitea.scitex-cloud.com
      user: <username>
      token: <api-token>
    env: dev | prod | staging

Note: passwords are technically allowed under ``workspace`` / ``gitea``
for unattended use, but env vars are strongly preferred. This docstring
deliberately does not prominently document the password key.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional

from scitex_config._ecosystem import local_state


def _candidate_paths(explicit: Optional[str]) -> list[Path]:
    """Return config file candidates in precedence order."""
    paths: list[Path] = []
    if explicit:
        paths.append(Path(explicit).expanduser())
    env_path = os.environ.get("SCITEX_CLOUD_CONFIG")
    if env_path:
        paths.append(Path(env_path).expanduser())
    paths.append(Path.cwd() / ".scitex" / "scitex-cloud.yaml")
    paths.append(local_state.path("cloud", "config.yaml"))
    return paths


def load_config(path: Optional[str] = None) -> Dict[str, Any]:
    """Load YAML config, returning ``{}`` if nothing is found/readable.

    Never raises on IO or parse errors — CLI commands should degrade
    gracefully to env vars / flags. Bad YAML just looks like "no
    config".

    Parameters
    ----------
    path : str, optional
        Explicit config path. Takes precedence over env/default paths.

    Returns
    -------
    dict
        Parsed YAML mapping, or ``{}`` if no config resolvable.
    """
    try:
        import yaml  # noqa: WPS433 (local import — optional dep)
    except ImportError:
        return {}

    for candidate in _candidate_paths(path):
        if not candidate.is_file():
            continue
        try:
            with candidate.open("r", encoding="utf-8") as fh:
                data = yaml.safe_load(fh) or {}
        except (OSError, yaml.YAMLError):
            continue
        if isinstance(data, dict):
            return data
        # Non-mapping top-level (list, scalar) is not a valid config.
        return {}
    return {}


def get_config_value(
    section: str,
    key: str,
    *,
    path: Optional[str] = None,
    default: Any = None,
) -> Any:
    """Fetch ``config[section][key]`` with graceful fallbacks."""
    cfg = load_config(path)
    section_data = cfg.get(section)
    if isinstance(section_data, dict):
        return section_data.get(key, default)
    return default


# EOF
