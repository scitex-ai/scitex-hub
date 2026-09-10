#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Hub's Django settings must load WITHOUT the scitex umbrella installed.

CARD: hub-settings-import-the-umbrella-for-one-decorator-20260818 (P1).

THE DEFECT THIS GUARDS. Until 2026-09-10, three settings modules opened with
``import scitex as stx``:

    config/settings/settings_shared.py:13
    config/settings/settings_auth.py:9
    config/settings/settings_integrations.py:10

so LOADING hub's settings required the ~40-package umbrella. The umbrella pins
its siblings EXACTLY (``scitex-ui==0.6.0`` and ~40 more), while hub declares
``scitex-ui>=0.20.0``. Any environment that could import settings therefore had
scitex-ui pinned to 0.6.0 -- which made
``tests/config/test_static_manifest.py::test_collectstatic_succeeds_with_hashed_urls``,
the guard on a PRODUCTION build step, structurally unrunnable against the
version hub's own pyproject declares.

AND THE IMPORT WAS HOLLOW. ``stx`` was used for exactly one thing per file: a
decorated no-op ``main()`` behind ``if __name__ == "__main__":``, whose own
docstring said it was not meant to be executed. Django IMPORTs a settings
module; it never runs one, so that guard could not fire. The measurement is on
the card. config/routing.py carried the same shape (``@stx.module`` on a dead
``main()``) and lost it in the same change.

WHY THE TEST IS A SUBPROCESS. The claim is "the settings import succeeds when
the umbrella is ABSENT", and the only honest way to assert an absence is to
remove it: a meta-path finder in a child interpreter makes ``scitex`` fail to
import the way a missing distribution does. In-process would be a lie -- by the
time this file's own process is importing anything, pytest has already imported
the test session's packages, and ``sys.modules`` is shared.

WHY THE CHILD SETS ITS OWN ENV, rather than inheriting the run's. Settings
declare their required variables loudly (``SCITEX_HUB_DJANGO_SECRET_KEY`` raises
a ValueError when unset, and settings_dev requires the Gitea SSH port). A test
that depended on the ambient run having them would pass locally and fail in CI,
or worse, the reverse. The values below are CI's own -- obviously fake, and the
same ones the pytest-matrix job exports.

THE POSITIVE CONTROL IS MANDATORY, not decoration: a blocker that silently
blocks nothing would make the main assertion pass on a tree that still imports
the umbrella. Two controls are asserted -- the blocker DOES stop the umbrella,
and the same child DOES fail when a package the settings genuinely need is
blocked. A guard that cannot fail is not a guard.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

#: CI's own values (see .github/workflows/pytest-matrix-on-ubuntu-py3-11-3-12-3-13.yml).
#: Explicit, not inherited: see the module docstring.
CHILD_ENV = {
    "SCITEX_HUB_DJANGO_SECRET_KEY": "ci-test-secret-do-not-use-in-prod",  # pragma: allowlist secret
    "SCITEX_HUB_GITEA_SSH_PORT_DEV": "2222",
    "SCITEX_HUB_TEST_MODE": "1",
}

_BLOCKER = '''
import sys


class _Blocked:
    """Make the named top-level packages unimportable, as an absent dist is."""

    def __init__(self, names):
        self.names = set(names)

    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in self.names:
            raise ModuleNotFoundError(
                f"No module named {fullname!r} (blocked by this test: the "
                "package is treated as not installed)"
            )
        return None


sys.meta_path.insert(0, _Blocked(BLOCKED))
'''


def _run_child(blocked: list[str], body: str) -> subprocess.CompletedProcess:
    """Run ``body`` in a child interpreter with ``blocked`` unimportable."""
    code = f"BLOCKED = {blocked!r}\n" + _BLOCKER + body
    env = {**os.environ, **CHILD_ENV}
    return subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(REPO),
        env=env,
        capture_output=True,
        text=True,
    )


def test_the_blocker_actually_blocks() -> None:
    # Arrange / Act -- the control for the tool, not for hub.
    result = _run_child(["scitex"], "import scitex\n")
    # Assert
    assert result.returncode != 0, (
        "the child imported 'scitex' with the blocker installed, so nothing "
        "below is a statement about an environment WITHOUT the umbrella."
    )
    assert "No module named" in result.stderr, result.stderr


def test_a_package_the_settings_need_cannot_be_blocked_either() -> None:
    # Arrange / Act -- the other control: the same child DOES fail when a
    # package the settings genuinely need is removed. Without this, a child
    # that never reached the import at all would read as success above.
    result = _run_child(
        ["django"],
        "import config.settings.settings_shared\n",
    )
    # Assert
    assert result.returncode != 0, (
        "blocking 'django' did not stop the settings import, so the child is "
        "not actually exercising the import chain."
    )


def test_settings_load_with_the_umbrella_absent() -> None:
    # Arrange / Act -- the claim on the card, asserted as an absence.
    result = _run_child(
        ["scitex"],
        "import config.settings.settings_shared\nprint('SETTINGS-IMPORTED')\n",
    )
    # Assert
    assert result.returncode == 0, (
        "importing config.settings.settings_shared failed with 'scitex' "
        "unimportable. Hub's settings must not require the umbrella: any "
        "environment that can load them has scitex-ui pinned to the "
        "umbrella's exact pin, which makes the production-build guard "
        "unrunnable against the version hub declares.\n"
        f"--- stderr ---\n{result.stderr}"
    )
    assert "SETTINGS-IMPORTED" in result.stdout


def test_every_settings_module_that_carried_the_umbrella_is_clean() -> None:
    # Arrange: the modules the card names, plus the routing module that carried
    # the same dead shape. Read from disk rather than imported, so this stays a
    # statement about the source and does not depend on the child above.
    names = (
        "config/settings/settings_shared.py",
        "config/settings/settings_auth.py",
        "config/settings/settings_integrations.py",
        "config/routing.py",
    )
    # Act
    offenders = [
        name
        for name in names
        if "import scitex as stx" in (REPO / name).read_text(encoding="utf-8")
    ]
    # Assert
    assert offenders == [], (
        f"{offenders} still import the umbrella. The settings chain is where "
        "it must not appear: the import exists only to decorate dead entry "
        "points, and it costs every environment that loads settings the "
        "umbrella's exact sibling pins."
    )
