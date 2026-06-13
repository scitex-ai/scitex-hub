#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pip-install user-published apps from the ``scitex-apps`` Gitea mirror.

F0 of the F0+F1 framework change (operator picked A, lead msg
34a4b271). The user-published-apps reframe (lead msg 9844e07c) puts
each approved app at ``scitex-apps/<repo>`` on Gitea; for the hub
Django process to ACTUALLY import + serve those apps' code, the
package has to land on PYTHONPATH. This module is the install
side; ``urls_user_apps.py`` is the URL-routing side.

Design choices:

  - Install via ``pip install --no-deps --target=<hub-managed-dir>``
    so the user-app's transitive deps do NOT pollute the hub venv.
    Deps the user-app declares in its pyproject get checked at
    activation time (PS-210 pattern); missing → loud error.
  - Target dir is ``<settings.SCITEX_HUB_USER_APPS_DIR>`` (defaults to
    ``<BASE_DIR>/data/user_apps/``) — added to ``sys.path`` at first
    activation so subsequent imports succeed.
  - The Gitea mirror's wheel URL is derived from the pinned commit
    (post-merge auto-pin in ``app_loader.pin_commit``) so installs
    are reproducible.
  - Fail-loud: any ``subprocess.run`` non-zero exits get raised
    rather than swallowed; ``_activate_approved_app`` MUST roll
    back the registration on install failure (caller's
    responsibility, this module just surfaces the error).

No skip_rules, no silent fallback. The default-dir fallback is a
documented production-image convention (mirrors how the
``settings.USER_DATA_ROOT`` default works in
``views/terminal/config``).
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

from django.conf import settings

logger = logging.getLogger(__name__)

#: Default install root if ``settings.SCITEX_HUB_USER_APPS_DIR`` is
#: unset; mirrors the production Docker image convention.
_DEFAULT_USER_APPS_DIR = Path("/app/data/user_apps")


def _user_apps_dir() -> Path:
    """Return the directory user-app packages land in."""
    configured = getattr(settings, "SCITEX_HUB_USER_APPS_DIR", None)
    if configured:
        return Path(configured)
    base_dir = getattr(settings, "BASE_DIR", None)
    if base_dir:
        return Path(base_dir) / "data" / "user_apps"
    return _DEFAULT_USER_APPS_DIR


def _ensure_on_path(install_dir: Path) -> None:
    """Prepend ``install_dir`` to ``sys.path`` if not already there."""
    install_dir_str = str(install_dir)
    if install_dir_str in sys.path:
        return
    sys.path.insert(0, install_dir_str)
    logger.info("[user_app_install] Added %s to sys.path", install_dir_str)


def _gitea_wheel_url(owner: str, repo: str, commit: str) -> str:
    """Return the Gitea archive URL for ``owner/repo`` at ``commit``.

    Pip can install from a tarball URL via ``pip install <url>``; this
    is simpler than uploading a built wheel to a registry.
    """
    base = getattr(settings, "GITEA_URL", None) or "http://gitea:3000"
    return f"{base.rstrip('/')}/{owner}/{repo}/archive/{commit}.tar.gz"


def pip_install_user_app(app_module) -> Path:
    """Install ``app_module``'s package into the user-apps dir.

    Idempotent: if the pinned commit is already installed (sentinel
    file ``<install_dir>/<module>/.scitex_hub_pinned_at`` matches), this
    is a no-op + just returns the install dir.

    Raises ``RuntimeError`` on any pip non-zero exit; the caller MUST
    roll back the app activation in that case (no half-state).
    """
    if not app_module.pinned_commit:
        raise RuntimeError(
            f"app_module '{app_module.module_name}' has no pinned_commit; "
            f"cannot install (call pin_commit() first)"
        )

    project = app_module.project
    if project is None:
        raise RuntimeError(
            f"app_module '{app_module.module_name}' has no project; "
            f"cannot derive the Gitea owner/repo for install"
        )

    owner = project.owner.username
    repo = project.slug
    commit = app_module.pinned_commit

    install_dir = _user_apps_dir()
    install_dir.mkdir(parents=True, exist_ok=True)

    pkg_dir = install_dir / app_module.module_name
    sentinel = pkg_dir / ".scitex_hub_pinned_at"
    if sentinel.is_file() and sentinel.read_text(encoding="utf-8").strip() == commit:
        logger.debug(
            "[user_app_install] '%s' already at pinned %s — skipping pip",
            app_module.module_name,
            commit[:8],
        )
        _ensure_on_path(install_dir)
        return install_dir

    url = _gitea_wheel_url(owner, repo, commit)
    logger.info(
        "[user_app_install] pip-installing %s from %s into %s",
        app_module.module_name,
        url,
        install_dir,
    )

    # Clean any previous version so --target doesn't get a stale tree.
    if pkg_dir.exists():
        shutil.rmtree(pkg_dir)

    env = os.environ.copy()
    env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--no-deps",
            "--target",
            str(install_dir),
            url,
        ],
        capture_output=True,
        text=True,
        env=env,
        timeout=300,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"pip install of '{app_module.module_name}' (commit {commit[:8]}) "
            f"failed with exit {result.returncode}:\n"
            f"--- stderr ---\n{result.stderr}\n"
            f"--- stdout ---\n{result.stdout}"
        )

    # Sentinel-stamp so the next activation skips the network round-trip.
    pkg_dir.mkdir(parents=True, exist_ok=True)
    sentinel.write_text(commit, encoding="utf-8")

    _ensure_on_path(install_dir)
    logger.info(
        "[user_app_install] Installed %s at %s (pinned %s)",
        app_module.module_name,
        pkg_dir,
        commit[:8],
    )
    return install_dir


# EOF
