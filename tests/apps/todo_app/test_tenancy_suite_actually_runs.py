"""Fail loudly when the board-tenancy suite would silently skip.

Every test in ``test_tenancy_store_channel_contract.py`` (and the wider
board-tenancy suite) is guarded by::

    pytestmark = pytest.mark.skipif(not _TODO_INSTALLED, ...)

That guard is correct — the middleware genuinely falls through when the
package is absent, so the assertions would be meaningless. But a skip is
invisible: pytest reports ``8 skipped``, exits 0, and the CI check goes
GREEN over a suite that tested nothing.

Measured 2026-08-09: that is exactly what happened. The tenancy contract
suite reported "8 skipped", exit 0, in an environment whose middleware was
byte-identical to prod's (sha256 8b7602aa…). It only passed once the real
package was installed by hand.

Those tests exist to stop ``middleware.py:211-213`` — the ``?store=``
injection that is the ONLY channel carrying tenancy to the board on
deployed prod (scitex_cards 0.32.1) — from being deleted. Skipped, they
protect nothing while reading as protection. A gate that cannot fail is
not a gate.

So this module holds the one assertion that must NOT be skipped in CI.
"""

import os

import pytest

from apps.workspace.todo_app.middleware import _TODO_INSTALLED

_MISSING_PACKAGE_HINT = (
    "scitex-cards/scitex-todo is NOT installed, so every board-tenancy test "
    "skips and this job reports green while asserting nothing.\n\n"
    "Fix: it belongs in the [dev] extra in pyproject.toml, which is what CI "
    "installs (uv pip install -e '.[all,dev]').\n\n"
    "Do NOT 'fix' this by deleting the skipif on the tenancy suite — the skip "
    "is correct for a local checkout without the package. The defect is the "
    "suite being green while unrun, not the skip itself."
)


@pytest.mark.skipif(
    not os.environ.get("CI"),
    reason=(
        "local/dev run: a missing package here is a normal working state. "
        "CI is where a silent skip becomes a false green."
    ),
)
def test_board_tenancy_suite_runs_instead_of_skipping_in_ci():
    """In CI the tenancy suite must RUN, not skip.

    Deliberately not guarded by ``_TODO_INSTALLED`` — guarding it would
    reproduce the very defect it exists to catch.
    """
    # Arrange: the guard every board-tenancy test keys off.
    expected_suite_runs = True

    # Act: read what that guard resolves to in this environment.
    suite_runs = _TODO_INSTALLED

    # Assert
    assert suite_runs is expected_suite_runs, _MISSING_PACKAGE_HINT
