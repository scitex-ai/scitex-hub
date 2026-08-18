"""Regression: a planted symlink must not let a read/write escape the jail.

The tenant-isolation primitive validate_path_in_project confines a target to a
root via ``target.resolve().relative_to(root.resolve())``. The load-bearing
detail for symlink safety is that ``.resolve()`` runs BEFORE the containment
check and ``.resolve()`` FOLLOWS symlinks: a symlink planted inside the jail
that points OUTSIDE resolves to its real out-of-jail target, so relative_to
raises ValueError and the access is rejected. See
apps/infra/project_app/services/filesystem/permissions.py:47.

This is a REAL gate, not a written warning. It plants an actual on-disk symlink
(jail/escape -> outside) and asserts the validator rejects a read THROUGH it. If
the guard is reverted so containment no longer resolves first (e.g.
``target.relative_to(root)`` or ``str(target).startswith(str(root))`` on the
UNRESOLVED path), the syntactic path stays under the jail, the validator returns
True, and this test FAILS loudly. Verified: the resolve()-removed form returns
True for exactly this symlink.

DB-FREE / MOCK-FREE by design (the security-regression CI gate runs
tests/security/ without Postgres and the linter forbids mocks): it calls the
pure validator directly with a real tmp filesystem — no ORM, no User row, no
network, no mock. The remote residual (validate_remote_path_in_root, which
deliberately does not resolve() a far-host path) is a documented, operator-
accepted LIMITATION and is out of scope for this local-jail gate.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.security


def test_validate_path_in_project_rejects_symlink_escape_from_jail(tmp_path):
    """A symlink inside the jail pointing OUTSIDE must be rejected (resolve()
    follows it, then containment fails)."""
    # Arrange
    from apps.infra.project_app.services.filesystem.permissions import (
        validate_path_in_project,
    )

    jail = tmp_path / "jail"
    jail.mkdir()
    outside = tmp_path / "outside_secret"
    outside.mkdir()
    (outside / "loot.txt").write_text("another tenant's secret")
    escape = jail / "escape"
    escape.symlink_to(outside, target_is_directory=True)
    smuggled = escape / "loot.txt"  # jail/escape -> outside; reads outside/loot.txt
    # Act
    allowed = validate_path_in_project(jail, smuggled)
    # Assert
    assert allowed is False


def test_validate_path_in_project_allows_a_real_file_inside_jail(tmp_path):
    """Positive control: a genuine file inside the jail is allowed, proving the
    escape gate above is not vacuously rejecting every path."""
    # Arrange
    from apps.infra.project_app.services.filesystem.permissions import (
        validate_path_in_project,
    )

    jail = tmp_path / "jail"
    (jail / "sub").mkdir(parents=True)
    inside = jail / "sub" / "real.txt"
    inside.write_text("mine")
    # Act
    allowed = validate_path_in_project(jail, inside)
    # Assert
    assert allowed is True