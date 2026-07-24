#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for visitor pool management.

Tests cover:
- Pool status reporting
- Visitor allocation and deallocation
- Session reuse and expiration handling

Security model (visitor-slot isolation audit 2026-07-07): allocation
only serves slots that are verified clean (``workspace_ready=True``,
``quarantined=False``) — so these tests bring slot 1 to that state via
the real reset pipeline, with the Gitea client and template clone
injected as tiny fakes through their seams. An expired allocation is
NOT immediately reusable anymore: it is lazily released into the reset
pipeline and only serves again after a verified re-clean.
"""

import shutil
from datetime import timedelta
from pathlib import Path

import pytest
from django.conf import settings
from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from apps.infra.project_app.models import Project, VisitorAllocation
from apps.infra.project_app.services.visitor_pool import VisitorPool
from apps.infra.project_app.services.visitor_pool.slot_lifecycle import (
    get_or_create_allocation,
    reset_and_verify_slot,
)
from apps.infra.project_app.services.visitor_pool.workspace_manager import (
    TEMPLATE_MARKER_RELPATH,
)


class MockSession(dict):
    """Mock Django session for testing."""

    def __init__(self, session_key="test-session-key"):
        super().__init__()
        self._session_key = session_key

    @property
    def session_key(self):
        return self._session_key

    def save(self):
        pass


class FakeGiteaClient:
    """In-memory Gitea client (no repos) for the reset pipeline."""

    def list_repositories(self, username):
        return []

    def delete_repository(self, owner, repo):
        return True


def fake_clone(template_id, dest, git_strategy=None):
    """Tiny real template clone mirroring the REAL ``.scitex/writer``
    layout (built from TEMPLATE_MARKER_RELPATH so fakes cannot diverge
    from the path production verifies — 2026-07-08 incident)."""
    manuscript = Path(dest) / TEMPLATE_MARKER_RELPATH / "01_manuscript"
    manuscript.mkdir(parents=True, exist_ok=True)
    (manuscript / "main.tex").write_text("% fresh template\n")
    return True


class NoContainerToolchain:
    """run_cmd fake: a host with no SLURM/apptainer binaries installed.

    The container-teardown step treats a missing binary as "nothing to
    tear down" (the dev/CI baseline). Injected through the reset
    pipeline's ``run_cmd`` seam so tests never touch a real cluster.
    """

    def __call__(self, argv, timeout=None):
        raise FileNotFoundError(argv[0])


NO_CONTAINER_HOST = NoContainerToolchain()


def _make_slot_ready(visitor_number: int) -> VisitorAllocation:
    """Bring a slot to the verified-clean, distributable state."""
    allocation = get_or_create_allocation(visitor_number)
    ok = reset_and_verify_slot(
        allocation,
        gitea_client=FakeGiteaClient(),
        clone_fn=fake_clone,
        run_cmd=NO_CONTAINER_HOST,
    )
    if not ok:
        raise RuntimeError("test setup: slot reset must succeed")
    allocation.refresh_from_db()
    return allocation


def _cleanup_workspace(username: str) -> None:
    """Remove the visitor's home root from THIS test's private BASE_DIR.

    The ``isolated_visitor_data_root`` autouse fixture in this
    directory's conftest repoints ``settings.BASE_DIR`` at a per-test
    ``tmp_path`` (autouse fixtures apply to ``django.test.TestCase``
    classes too, and run before ``setUp``), so this ``rmtree`` can only
    ever touch the current test's own tree — not a directory shared by
    every xdist worker (CI run 29918531942).
    """
    base = Path(settings.BASE_DIR) / "data" / "users" / username
    if base.exists():
        shutil.rmtree(base, ignore_errors=True)


def _create_visitor_user_and_project():
    """Ensure the visitor-001 user and its default project exist."""
    user, _ = User.objects.get_or_create(
        username="visitor-001",
        defaults={"email": "visitor001@example.com"},
    )
    if not user.has_usable_password():
        user.set_password("testpass123")
        user.save()
    project, _ = Project.objects.get_or_create(
        slug="default-project",
        owner=user,
        defaults={"name": "Default Project"},
    )
    return user, project


class TestVisitorPoolStatus(TestCase):
    """Test pool status reporting."""

    def test_get_pool_status_contains_expected_keys(self):
        # Arrange
        expected_keys = {"total", "allocated", "free", "expired"}
        # Act
        status = VisitorPool.get_pool_status()
        # Assert
        assert expected_keys <= set(status)

    def test_get_pool_status_total_matches_pool_size(self):
        # Arrange
        expected_total = VisitorPool.POOL_SIZE
        # Act
        status = VisitorPool.get_pool_status()
        # Assert
        assert status["total"] == expected_total

    def test_get_pool_status_free_count_is_non_negative(self):
        # Arrange
        # (fresh test database: no allocations)
        # Act
        status = VisitorPool.get_pool_status()
        # Assert
        assert status["free"] >= 0

    def test_get_pool_status_allocated_count_is_non_negative(self):
        # Arrange
        # (fresh test database: no allocations)
        # Act
        status = VisitorPool.get_pool_status()
        # Assert
        assert status["allocated"] >= 0


class TestVisitorAllocation(TestCase):
    """Test visitor slot allocation (verified-clean slots only)."""

    def setUp(self):
        """Slot 1 exists and is verified clean (ready gate satisfied)."""
        self.visitor_user, self.visitor_project = _create_visitor_user_and_project()
        VisitorAllocation.objects.filter(visitor_number=1).delete()
        self.allocation = _make_slot_ready(1)

    def tearDown(self):
        _cleanup_workspace("visitor-001")

    def test_allocate_verified_ready_slot_returns_project(self):
        # Arrange
        session = MockSession("test-alloc-success")
        # Act
        project, user = VisitorPool.allocate_visitor(session)
        # Assert
        assert project is not None

    def test_allocate_verified_ready_slot_returns_visitor_user(self):
        # Arrange
        session = MockSession("test-alloc-success")
        # Act
        project, user = VisitorPool.allocate_visitor(session)
        # Assert
        assert user == self.visitor_user

    def test_allocate_stores_allocation_token_in_session(self):
        # Arrange
        session = MockSession("test-session-data")
        # Act
        VisitorPool.allocate_visitor(session)
        # Assert
        assert VisitorPool.SESSION_KEY_ALLOCATION_TOKEN in session

    def test_allocate_stores_project_id_in_session(self):
        # Arrange
        session = MockSession("test-session-data")
        # Act
        VisitorPool.allocate_visitor(session)
        # Assert
        assert VisitorPool.SESSION_KEY_PROJECT_ID in session

    def test_allocate_stores_visitor_id_in_session(self):
        # Arrange
        session = MockSession("test-session-data")
        # Act
        VisitorPool.allocate_visitor(session)
        # Assert
        assert VisitorPool.SESSION_KEY_VISITOR_ID in session

    def test_allocate_visitor_reuses_existing_valid_allocation(self):
        # Arrange
        session = MockSession("test-reuse")
        VisitorPool.allocate_visitor(session)
        token_first = session.get(VisitorPool.SESSION_KEY_ALLOCATION_TOKEN)
        # Act
        VisitorPool.allocate_visitor(session)
        token_second = session.get(VisitorPool.SESSION_KEY_ALLOCATION_TOKEN)
        # Assert
        assert token_first == token_second

    def test_deallocate_visitor_removes_allocation_token(self):
        # Arrange
        session = MockSession("test-dealloc")
        VisitorPool.allocate_visitor(session)
        # Act
        VisitorPool.deallocate_visitor(session)
        # Assert
        assert VisitorPool.SESSION_KEY_ALLOCATION_TOKEN not in session

    def test_deallocate_visitor_removes_project_id(self):
        # Arrange
        session = MockSession("test-dealloc")
        VisitorPool.allocate_visitor(session)
        # Act
        VisitorPool.deallocate_visitor(session)
        # Assert
        assert VisitorPool.SESSION_KEY_PROJECT_ID not in session

    def test_deallocate_visitor_removes_visitor_id(self):
        # Arrange
        session = MockSession("test-dealloc")
        VisitorPool.allocate_visitor(session)
        # Act
        VisitorPool.deallocate_visitor(session)
        # Assert
        assert VisitorPool.SESSION_KEY_VISITOR_ID not in session


class TestVisitorAllocationExpiration(TestCase):
    """Expired allocations enter the reset pipeline before reuse."""

    def setUp(self):
        """Slot 1 is ready, then made active-but-expired (dirty)."""
        self.visitor_user, self.visitor_project = _create_visitor_user_and_project()
        VisitorAllocation.objects.filter(visitor_number=1).delete()
        self.allocation = _make_slot_ready(1)
        self.allocation.session_key = "old-session"
        self.allocation.allocation_token = "expired-token"
        self.allocation.expires_at = timezone.now() - timedelta(hours=1)
        self.allocation.is_active = True
        self.allocation.save()

    def tearDown(self):
        _cleanup_workspace("visitor-001")

    def test_expired_allocation_is_not_served_before_reverify(self):
        # Arrange
        session = MockSession("new-session")
        # Act: the expired slot is dirty — allocation must refuse it
        project, user = VisitorPool.allocate_visitor(session)
        # Assert
        assert project is None

    def test_expired_allocation_is_released_lazily_on_allocation_attempt(self):
        # Arrange
        session = MockSession("new-session")
        # Act
        VisitorPool.allocate_visitor(session)
        self.allocation.refresh_from_db()
        # Assert
        assert (self.allocation.is_active, self.allocation.workspace_ready) == (
            False,
            False,
        )

    def test_expired_slot_serves_again_after_verified_reclean(self):
        # Arrange: first attempt lazily releases the expired slot
        session = MockSession("new-session")
        VisitorPool.allocate_visitor(session)
        self.allocation.refresh_from_db()
        # Act: the reset pipeline verifies the slot clean, then reallocate
        reset_and_verify_slot(
            self.allocation,
            gitea_client=FakeGiteaClient(),
            clone_fn=fake_clone,
            run_cmd=NO_CONTAINER_HOST,
        )
        project, user = VisitorPool.allocate_visitor(session)
        # Assert
        assert project is not None

    def test_cleanup_expired_allocations_deactivates(self):
        # Arrange
        # (setUp created an active, expired allocation)
        # Act
        VisitorPool.cleanup_expired_allocations()
        self.allocation.refresh_from_db()
        # Assert
        assert not self.allocation.is_active


class TestPoolAllocatorEdgeCases(TestCase):
    """Test edge cases in pool allocation."""

    def test_deallocate_without_allocation_leaves_session_empty(self):
        # Arrange
        session = MockSession("no-alloc")
        # Act: must not raise
        VisitorPool.deallocate_visitor(session)
        # Assert
        assert VisitorPool.SESSION_KEY_ALLOCATION_TOKEN not in session

    def test_deallocate_with_invalid_token_does_not_raise(self):
        # Arrange
        session = MockSession("invalid-token-session")
        session[VisitorPool.SESSION_KEY_ALLOCATION_TOKEN] = "invalid-token-xyz"
        # Act: must not raise (unknown token is logged, not fatal)
        result = VisitorPool.deallocate_visitor(session)
        # Assert
        assert result is None


class TestVisitorPoolConstants(TestCase):
    """Test visitor pool constants and configuration."""

    def test_visitor_user_prefix_matches_convention(self):
        # Arrange
        expected_prefix = "visitor-"
        # Act
        prefix = VisitorPool.VISITOR_USER_PREFIX
        # Assert
        assert prefix == expected_prefix

    def test_session_lifetime_is_one_hour(self):
        # Arrange
        expected_hours = 1
        # Act
        lifetime = VisitorPool.SESSION_LIFETIME_HOURS
        # Assert
        assert lifetime == expected_hours

    def test_pool_size_is_at_least_one(self):
        # Arrange
        minimum = 1
        # Act
        pool_size = VisitorPool.POOL_SIZE
        # Assert
        assert pool_size >= minimum

    def test_required_session_keys_are_defined(self):
        # Arrange
        key_names = (
            "SESSION_KEY_PROJECT_ID",
            "SESSION_KEY_VISITOR_ID",
            "SESSION_KEY_ALLOCATION_TOKEN",
        )
        # Act
        defined = tuple(hasattr(VisitorPool, name) for name in key_names)
        # Assert
        assert defined == (True, True, True)


if __name__ == "__main__":
    import os

    pytest.main([os.path.abspath(__file__), "-v"])
