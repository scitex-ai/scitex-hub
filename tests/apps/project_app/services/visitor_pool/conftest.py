#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Per-test filesystem isolation for the visitor-pool suite.

WHY THIS EXISTS
---------------
CI run 29918531942 (branch ``ci/unify-canonical-caller``) reported
``15 failed, 2257 passed, 848 skipped, 18 errors``. Seventeen of the
eighteen errors were one identical ERROR-at-setup:
``RuntimeError: fixture reset must succeed``.

Every module in this directory drives the REAL visitor reset pipeline,
and that pipeline writes to a path derived from the visitor's identity::

    settings.BASE_DIR / "data" / "users" / <username>          (home root)
    settings.MEDIA_ROOT / "user_containers" / <user id>        (SIF builds)

Six modules here hardcode the SAME identity (``visitor-001``) and so the
SAME absolute directory:

* ``test_slot_recycling_security.py`` (``_base_path_for`` / ``visitor-001``)
* ``test_container_wipe_security.py`` (``USERNAME = "visitor-001"``)
* ``test_visitor_pool.py`` (``_cleanup_workspace`` / ``visitor-001``)
* ``test_pool_manager.py``, ``test_reconcile_visitor_slots.py``,
  ``test_home_skeleton_reality.py`` (same root, same identity)

pytest-django gives each xdist worker its own DATABASE. It does NOT give
each worker its own FILESYSTEM. With ``-n auto`` resolving to ~128
workers on the CI runner, ~128 processes created and ``rmtree``-d that
one directory concurrently: worker A's teardown deleted the tree worker
B was mid-clone in, ``reset_and_verify_slot`` returned falsy, and the
fixture raised. The log names the exact casualty::

    reset failed: home skeleton recreation failed for visitor-001:
    [errno 2] no such file or directory: 'proj/dotfiles/bashrc' ->
    '.../scitex-hub/data/users/visitor-001/.bashrc'

WHY NOT A GROUPING DIRECTIVE
----------------------------
``--dist loadfile`` / ``xdist_group`` / a serial marker were rejected.
They would not even work — the collision is CROSS-MODULE, so
``loadfile`` still lands six modules on six workers all hammering
``data/users/visitor-001``. More importantly, these modules assert that
a recycled slot leaks NOTHING to the next visitor
(``test_zero_filesystem_residue_after_recycle``,
``test_gitea_repos_do_not_survive_recycle``,
``test_chat_rows_do_not_survive_recycle``,
``test_recycled_slot_serves_next_visitor``). Pinning them to one worker
would turn them green while leaving those assertions running against a
directory any other test can still stomp — deleting the alarm, not the
fire. Isolating the tree per test is what lets those assertions be
evaluated on their own merits.
"""

import pytest
from django.test import override_settings


@pytest.fixture(autouse=True)
def isolated_visitor_data_root(tmp_path):
    """Give this test its own visitor-data tree.

    ``BASE_DIR`` and ``MEDIA_ROOT`` are the only two roots the reset
    pipeline writes under, and every production call site reads them
    through ``django.conf.settings`` at CALL time (never captured at
    import), so overriding them here relocates the whole tree without a
    single change to production code. The fresh skeleton is generated in
    place by ``create_dotfiles_repo`` rather than copied out of the
    repo, so nothing in the pipeline needs the real ``BASE_DIR``.

    ``tmp_path`` is unique per test AND per xdist worker, so no two
    tests — parallel or sequential — can share visitor state. Autouse
    covers the ``django.test.TestCase`` modules here too: pytest sets up
    autouse fixtures before ``setUp`` runs.
    """
    base_dir = tmp_path / "hub"
    media_root = tmp_path / "media"
    (base_dir / "data" / "users").mkdir(parents=True)
    media_root.mkdir(parents=True)
    with override_settings(BASE_DIR=base_dir, MEDIA_ROOT=str(media_root)):
        yield base_dir


# EOF
