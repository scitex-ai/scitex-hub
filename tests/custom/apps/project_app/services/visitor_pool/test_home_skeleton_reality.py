#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reality lock: the recycled-home skeleton constants must equal what the
REAL skeleton builder creates (drift guard — isolation audit gap #6 follow-up).

``home_state.verify_recycled_home`` is the filesystem half of the visitor-slot
FINAL GATE: it asserts a recycled home holds EXACTLY
:data:`EXPECTED_HOME_ENTRIES` and its ``proj/`` holds EXACTLY
:data:`EXPECTED_PROJ_ENTRIES`. Both sets are HARDCODED. The skeleton they
describe is built by :func:`recreate_workspace_skeleton`, which runs the SAME
two real producers a normal terminal spawn uses:

* the ``project_filesystem`` manager init -> ``proj/`` + ``proj/workspace_info.json``
* ``ensure_workspace_sync`` (+ the ``dotfiles`` setup) -> ``.singularity/``,
  ``proj/default-project/``, ``proj/dotfiles/`` and the home-level dotfile
  symlinks (``.bashrc`` ... ``.ipython``).

Risk this guards (the fleet has already hit its sibling): if that skeleton ever
DRIFTS — a dev adds/renames a dotfile symlink, adds a top-level home dir, or a
proj-level file — the hardcoded gate stops matching and false-quarantines EVERY
visitor slot (the "all-16-slots-quarantined" outage the template-marker drift
caused on 2026-07-08). This test runs the REAL builder into a throwaway home
and asserts the constants still equal its output, so drift goes RED here in CI
instead of silently bricking prod.

Why a reality TEST and not runtime derivation of the constants: the ~11
skeleton entries originate from four functions across three modules, and only
the five dotfile symlinks live in a (function-local, unexported) dict — a clean
static derivation would need a multi-module refactor of shared terminal-spawn
code. A *runtime* derivation (re-running the skeleton inside the security
verify hot-path) is worse still: deriving the expectation from the same code
that produces the artifact can no longer catch a leaked entry, and a transient
temp/git failure would itself false-quarantine — the very outcome this gate
exists to prevent. So the production gate stays a fixed, auditable, cheap
constant and THIS test locks it to reality. Mirrors the sibling lock
``test_template_marker_reality.py``.

Run (SQLite, no network — the skeleton is pure filesystem + a local ``git``):

    SCITEX_HUB_DJANGO_SECRET_KEY=local-test-secret \
    SCITEX_HUB_GITEA_SSH_PORT_DEV=2222 \
    SCITEX_HUB_USE_SQLITE_DEV=1 \
    /opt/venv-sac/bin/python3 -m pytest <abs path to this file>
"""

import shutil
from pathlib import Path

import pytest
from django.conf import settings
from django.contrib.auth.models import User

from apps.infra.project_app.services.visitor_pool.home_state import (
    EXPECTED_HOME_ENTRIES,
    EXPECTED_PROJ_ENTRIES,
    recreate_workspace_skeleton,
    verify_recycled_home,
)
from apps.infra.project_app.services.visitor_pool.workspace_manager import (
    WorkspaceManager,
)

USERNAME = "visitor-skeleton-reality"
PROJECT_SLUG = WorkspaceManager.DEFAULT_PROJECT_SLUG


def _home_root_for(username: str) -> Path:
    return Path(settings.BASE_DIR) / "data" / "users" / username


@pytest.fixture
def real_skeleton_home(db):
    """Build the recycled-home skeleton with the REAL producers.

    Creates a visitor user and runs the real ``recreate_workspace_skeleton``
    (project_filesystem manager init + ``ensure_workspace_sync`` + dotfiles)
    into ``data/users/<username>/`` — no fakes, no network, no apptainer.
    Yields ``(user, home_root)``; the on-disk tree is removed afterwards (the
    DB row is rolled back by the ``db`` fixture, but the filesystem is not).
    """
    user = User.objects.create(username=USERNAME, email=f"{USERNAME}@visitor.local")
    home = _home_root_for(USERNAME)
    if home.exists():
        shutil.rmtree(home, ignore_errors=True)
    recreate_workspace_skeleton(user, PROJECT_SLUG)
    yield user, home
    if home.exists():
        shutil.rmtree(home, ignore_errors=True)


class TestHomeSkeletonMatchesGateConstants:
    def test_expected_home_entries_equals_real_skeleton(self, real_skeleton_home):
        # Arrange
        _user, home = real_skeleton_home
        # Act
        actual = {p.name for p in home.iterdir()}
        # Assert — set equality reports BOTH drift directions (extra = leak
        # surface, missing = skeleton gap) in the failure diff.
        assert actual == set(EXPECTED_HOME_ENTRIES)

    def test_expected_proj_entries_equals_real_skeleton(self, real_skeleton_home):
        # Arrange
        _user, home = real_skeleton_home
        # Act
        actual = {p.name for p in (home / "proj").iterdir()}
        # Assert
        assert actual == set(EXPECTED_PROJ_ENTRIES)

    def test_real_skeleton_passes_production_verify_gate(self, real_skeleton_home):
        # Arrange: strongest lock — the REAL final gate must accept the REAL
        # freshly-built skeleton. No clone is needed: the gate checks
        # proj-level entry NAMES, an empty ``~/.singularity``, and the
        # absence of a user_containers build dir — all true after a bare
        # skeleton recreation. Drift that broke the constants raises here.
        user, home = real_skeleton_home
        # Act
        gate_result = verify_recycled_home(user, home)
        # Assert — returns None (no HomeStateError) when reality matches the gate.
        assert gate_result is None


if __name__ == "__main__":
    import os

    pytest.main([os.path.abspath(__file__)])
