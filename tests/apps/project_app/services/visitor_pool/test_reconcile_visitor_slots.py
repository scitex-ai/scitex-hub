#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for the reconcile_visitor_slots recovery path.

Guards two invariants from the prod 2026-07-09 incident:

* Reconciling a slot RELEASES its stale ``is_active`` allocation (the old
  session is invalid once the slot is re-cleaned) — so a wiped slot can
  never keep a zombie allocation that wedges the pool.
* A slot that fails wipe/verify stays QUARANTINED and is never returned to
  the distributable pool (``ready``) — the clean-verify security gate is
  not bypassed by the release/reconcile path.

Real DB via pytest-django ``TestCase``; the reset pipeline runs for real
with the Gitea client and template clone injected as tiny fakes through
their seams — no mocks (STX-NM001).
"""

import secrets
import shutil
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from apps.infra.project_app.models import Project, VisitorAllocation
from apps.infra.project_app.services.visitor_pool import VisitorPool
from apps.infra.project_app.services.visitor_pool.slot_lifecycle import (
    get_or_create_allocation,
    quarantine_slot,
    reset_and_verify_slot,
)
from apps.infra.project_app.services.visitor_pool.workspace_manager import (
    TEMPLATE_MARKER_RELPATH,
)


class MockSession(dict):
    """Real dict-backed Django session stand-in (not a unittest mock)."""

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
    """Real, tiny template clone mirroring the ``.scitex/writer`` layout."""
    manuscript = Path(dest) / TEMPLATE_MARKER_RELPATH / "01_manuscript"
    manuscript.mkdir(parents=True, exist_ok=True)
    (manuscript / "main.tex").write_text("% fresh template\n")
    return True


def _boom_clone(template_id, dest, git_strategy=None):
    raise RuntimeError("simulated clone failure")


def _create_visitor_user_and_project():
    user, _ = User.objects.get_or_create(
        username="visitor-001", defaults={"email": "v001@example.com"}
    )
    Project.objects.get_or_create(
        slug="default-project",
        owner=user,
        defaults={"name": "Default Project"},
    )
    return user


def _stale_active_slot(number=1):
    """A slot allocated an hour ago and never cleanly released (zombie)."""
    now = timezone.now()
    return VisitorAllocation.objects.create(
        visitor_number=number,
        session_key="old-session",
        allocation_token=secrets.token_hex(16),
        expires_at=now - timedelta(hours=1),
        is_active=True,
        last_activity=now - timedelta(days=7),
        workspace_ready=True,
    )


class TestReconcileQuarantineOnly(TestCase):
    """--quarantine-only releases stale allocations without a re-clean."""

    def setUp(self):
        VisitorAllocation.objects.filter(visitor_number=1).delete()
        self.allocation = _stale_active_slot(1)

    def test_quarantine_only_deactivates_stale_allocation(self):
        # Arrange: setUp created a stale is_active zombie slot.
        # Act
        call_command("reconcile_visitor_slots", visitor=1, quarantine_only=True)
        self.allocation.refresh_from_db()
        # Assert: the zombie is_active row is released.
        assert self.allocation.is_active is False

    def test_quarantine_only_marks_slot_quarantined(self):
        # Arrange: setUp created a stale is_active zombie slot.
        # Act
        call_command("reconcile_visitor_slots", visitor=1, quarantine_only=True)
        self.allocation.refresh_from_db()
        # Assert
        assert self.allocation.quarantined is True


class TestReconcileRecleanReturnsSlot(TestCase):
    """A clean re-verify returns the slot to the pool and clears is_active."""

    def setUp(self):
        self.user = _create_visitor_user_and_project()
        VisitorAllocation.objects.filter(visitor_number=1).delete()
        self.allocation = _stale_active_slot(1)

    def tearDown(self):
        base = Path(settings.BASE_DIR) / "data" / "users" / "visitor-001"
        if base.exists():
            shutil.rmtree(base, ignore_errors=True)

    def test_clean_reverify_releases_stale_allocation(self):
        # Arrange: setUp created a stale is_active zombie + its user/project.
        # Act
        reset_and_verify_slot(
            self.allocation, gitea_client=FakeGiteaClient(), clone_fn=fake_clone
        )
        self.allocation.refresh_from_db()
        # Assert
        assert self.allocation.is_active is False

    def test_clean_reverify_returns_slot_to_ready_pool(self):
        # Arrange: setUp created a stale is_active zombie + its user/project.
        # Act
        reset_and_verify_slot(
            self.allocation, gitea_client=FakeGiteaClient(), clone_fn=fake_clone
        )
        self.allocation.refresh_from_db()
        # Assert: distributable again (workspace_ready, not quarantined).
        assert (self.allocation.workspace_ready, self.allocation.quarantined) == (
            True,
            False,
        )


class TestReconcileFailedRecleanQuarantines(TestCase):
    """A failed wipe/verify quarantines the slot — never freed to the pool."""

    def setUp(self):
        self.user = _create_visitor_user_and_project()
        VisitorAllocation.objects.filter(visitor_number=1).delete()
        self.allocation = _stale_active_slot(1)

    def tearDown(self):
        base = Path(settings.BASE_DIR) / "data" / "users" / "visitor-001"
        if base.exists():
            shutil.rmtree(base, ignore_errors=True)

    def test_failed_reclean_quarantines_slot(self):
        # Arrange: setUp created a stale is_active zombie + its user/project.
        # Act: the clone blows up mid-reset.
        ok = reset_and_verify_slot(
            self.allocation, gitea_client=FakeGiteaClient(), clone_fn=_boom_clone
        )
        self.allocation.refresh_from_db()
        # Assert
        assert (ok, self.allocation.quarantined) == (False, True)

    def test_quarantined_slot_is_not_counted_ready(self):
        # Arrange: setUp created a stale is_active zombie + its user/project.
        # Act
        reset_and_verify_slot(
            self.allocation, gitea_client=FakeGiteaClient(), clone_fn=_boom_clone
        )
        status = VisitorPool.get_pool_status()
        # Assert: a quarantined slot is never distributable.
        assert status["ready"] == 0


class TestQuarantinedSlotNotServed(TestCase):
    """The allocator refuses a quarantined slot even if its files look ok."""

    def setUp(self):
        self.user = _create_visitor_user_and_project()
        VisitorAllocation.objects.filter(visitor_number=1).delete()
        allocation = get_or_create_allocation(1)
        quarantine_slot(allocation, "test: forced quarantine")

    def test_allocator_refuses_quarantined_slot(self):
        # Arrange: slot 1 is quarantined (setUp), user/project exist.
        session = MockSession("quarantined-refuse")
        # Act
        project, _ = VisitorPool.allocate_visitor(session)
        # Assert
        assert project is None


if __name__ == "__main__":
    import os

    import pytest

    pytest.main([os.path.abspath(__file__), "-v"])
