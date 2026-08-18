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
  - Target dir is ``<settings.SCITEX_HUB_USER_APPS_DIR>`` (defaults to
    ``<BASE_DIR>/data/user_apps/``) — added to ``sys.path`` at first
    activation so subsequent imports succeed.
  - The Gitea mirror's tarball URL is derived from the pinned commit
    so installs are reproducible.
  - Fail-loud: any ``subprocess.run`` non-zero exits get raised
    rather than swallowed; ``_activate_approved_app`` MUST roll
    back the registration on install failure (caller's
    responsibility, this module just surfaces the error).

SECURITY (per lead msg 37b38d69 + CodeQL HIGH alerts on PR #290 v1):
every user-controlled string that feeds a filesystem path OR a
subprocess argument goes through a STRICT regex validator
(``_safe_identifier`` / ``_safe_commit``) FIRST. Module name,
Gitea owner, Gitea repo, commit SHA all rejected hard if they
contain ``/`` ``..`` or any non-allowlisted character. No silent
fallback, no path normalization that could be bypassed.

Log statements use ``%r`` (repr) on user-string args so control
chars / newlines from a malicious submission can't inject fake
log lines.
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from django.conf import settings
from django.utils._os import safe_join

logger = logging.getLogger(__name__)

#: Default install root if ``settings.SCITEX_HUB_USER_APPS_DIR`` is
#: unset; mirrors the production Docker image convention.
_DEFAULT_USER_APPS_DIR = Path("/app/data/user_apps")

#: Python-identifier-shaped regex. Matches the python-module-name
#: convention + rejects every char that could escape a filesystem
#: path or smuggle into a subprocess arg. ``a/b`` ``../evil`` ``..``
#: ``a;rm -rf /`` all fail.
_IDENT_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")

#: Git SHA — hex digits, length 7-64 (short-SHA through full SHA-256).
_COMMIT_RE = re.compile(r"^[0-9a-fA-F]{7,64}$")


def _safe_identifier(name: str, field: str) -> str:
    """Validate ``name`` against ``_IDENT_RE``; raise ValueError if not.

    Used for module_name, Gitea owner, Gitea repo — anything that gets
    interpolated into a filesystem path or subprocess argv.
    """
    if not isinstance(name, str) or not _IDENT_RE.match(name):
        raise ValueError(
            f"unsafe value for {field}: {name!r} — must match "
            f"{_IDENT_RE.pattern} (Python-identifier shape; no '/' '..' or "
            f"shell metachars)"
        )
    return name


def _safe_commit(commit: str) -> str:
    """Validate Git SHA; raise ValueError if not."""
    if not isinstance(commit, str) or not _COMMIT_RE.match(commit):
        raise ValueError(
            f"unsafe value for commit: {commit!r} — must match "
            f"{_COMMIT_RE.pattern} (hex SHA, 7-64 chars)"
        )
    return commit


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
    logger.info("[user_app_install] Added %r to sys.path", install_dir_str)


def _gitea_wheel_url(owner: str, repo: str, commit: str) -> str:
    """Return the Gitea archive URL for ``owner/repo`` at ``commit``.

    Inputs assumed pre-validated by the caller (raises in
    :func:`pip_install_user_app` before this is reached).
    """
    base = getattr(settings, "GITEA_URL", None) or "http://gitea:3000"
    return f"{base.rstrip('/')}/{owner}/{repo}/archive/{commit}.tar.gz"


def pip_install_user_app(app_module) -> Path:
    """Install ``app_module``'s package into the user-apps dir.

    SECURITY: ``module_name``, Gitea ``owner``, ``repo``, and the
    pinned ``commit`` SHA are validated against strict regexes BEFORE
    any filesystem path or subprocess call sees them. A malicious
    submission with ``module_name='../evil'`` (or any other traversal
    shape) raises ValueError immediately and nothing is touched.

    Idempotent: if the pinned commit is already installed (sentinel
    file ``<install_dir>/<module>/.scitex_hub_pinned_at`` matches), this
    is a no-op + just returns the install dir.

    Raises ``RuntimeError`` on any pip non-zero exit; ``ValueError``
    on validation failure. The caller MUST roll back the app
    activation in either case (no half-state).
    """
    if not app_module.pinned_commit:
        raise RuntimeError(
            f"app_module {app_module.module_name!r} has no pinned_commit; "
            f"cannot install (call pin_commit() first)"
        )

    project = app_module.project
    if project is None:
        raise RuntimeError(
            f"app_module {app_module.module_name!r} has no project; "
            f"cannot derive the Gitea owner/repo for install"
        )

    # STRICT VALIDATION — every user-controlled string before path/subprocess.
    module_name = _safe_identifier(app_module.module_name, "module_name")
    owner = _safe_identifier(project.owner.username, "gitea_owner")
    repo = _safe_identifier(project.slug, "gitea_repo")
    commit = _safe_commit(app_module.pinned_commit)

    install_dir = _user_apps_dir()
    install_dir.mkdir(parents=True, exist_ok=True)

    # SANITIZATION via Django's `safe_join` (lead msg e40711ed path
    # β+γ): Django's safe-path-join is the FileSystemStorage primitive
    # — joins base+segment, raises SuspiciousFileOperation if the
    # result escapes base, returns the sanitized path STRING. Because
    # `pkg_dir` and `sentinel` come OUT of `safe_join`, CodeQL sees
    # them as sanitized AT THE SOURCE; all downstream uses inherit
    # the clean flow (which the v3 helper + v4 inline-is_relative_to
    # patterns failed to propagate, see PR #290 v3/v4 CodeQL re-runs).
    # `_safe_identifier` regex still runs first as defense-in-depth.
    pkg_dir = Path(safe_join(str(install_dir), module_name))
    sentinel = Path(safe_join(str(pkg_dir), ".scitex_hub_pinned_at"))
    if sentinel.is_file() and sentinel.read_text(encoding="utf-8").strip() == commit:
        logger.debug(
            "[user_app_install] %r already at pinned %s — skipping pip",
            module_name,
            commit[:8],
        )
        _ensure_on_path(install_dir)
        return install_dir

    url = _gitea_wheel_url(owner, repo, commit)
    logger.info(
        "[user_app_install] pip-installing %r from %r into %r",
        module_name,
        url,
        str(install_dir),
    )

    # Clean any previous version so --target doesn't get a stale tree.
    if pkg_dir.exists():
        shutil.rmtree(pkg_dir)

    env = os.environ.copy()
    env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    result = subprocess.run(  # noqa: S603 - argv is list, no shell; url validated
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
            f"pip install of {module_name!r} (commit {commit[:8]}) "
            f"failed with exit {result.returncode}:\n"
            f"--- stderr ---\n{result.stderr}\n"
            f"--- stdout ---\n{result.stdout}"
        )

    # Sentinel-stamp so the next activation skips the network round-trip.
    pkg_dir.mkdir(parents=True, exist_ok=True)
    sentinel.write_text(commit, encoding="utf-8")

    _ensure_on_path(install_dir)
    logger.info(
        "[user_app_install] Installed %r at %r (pinned %s)",
        module_name,
        str(pkg_dir),
        commit[:8],
    )
    return install_dir


# EOF
