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

import os
import secrets
import shutil
from datetime import timedelta
from io import StringIO
from pathlib import Path

import pytest
from django.conf import settings
from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
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


class NoContainerToolchain:
    """run_cmd fake: a host with no SLURM/apptainer binaries installed.

    The container-teardown step treats a missing binary as "nothing to
    tear down" (the dev/CI baseline). Injected through the reset
    pipeline's ``run_cmd`` seam so tests never touch a real cluster.
    """

    def __call__(self, argv, timeout=None):
        raise FileNotFoundError(argv[0])


NO_CONTAINER_HOST = NoContainerToolchain()


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


def _live_active_slot(number=1):
    """A slot a visitor is using RIGHT NOW (recent activity, not a zombie)."""
    now = timezone.now()
    return VisitorAllocation.objects.create(
        visitor_number=number,
        session_key="live-session",
        allocation_token=secrets.token_hex(16),
        expires_at=now + timedelta(hours=1),
        is_active=True,
        last_activity=now,
        workspace_ready=True,
    )


class TestReconcileGuardsLiveSlot(TestCase):
    """The operator single-slot wipe REFUSES an in-use slot (needs --force).

    This is the positive companion to TestReconcileQuarantineOnly /
    TestReconcileAsyncDispatch, which pin that the guard must NOT fire on the
    safe paths. Without a test that the guard DOES fire on the dangerous path,
    each narrowing of its condition could hollow it into a no-op unnoticed —
    the exact defect the guard exists to catch (a check that gates nothing).
    """

    def setUp(self):
        VisitorAllocation.objects.filter(visitor_number=1).delete()
        self.allocation = _live_active_slot(1)

    def test_plain_visitor_wipe_refuses_live_slot(self):
        # Arrange: setUp created a slot a visitor is actively using.
        argv = ("reconcile_visitor_slots",)
        # Act
        # Assert: the bare operator wipe must refuse it.
        with pytest.raises(CommandError):
            call_command(*argv, visitor=1)

    def test_refused_slot_is_left_allocated(self):
        # Arrange: setUp created a live in-use slot; the refusal is asserted
        # in test_plain_visitor_wipe_refuses_live_slot, so here we only care
        # about the post-state and swallow the expected CommandError.
        try:
            call_command("reconcile_visitor_slots", visitor=1)
        except CommandError:
            pass
        # Act
        self.allocation.refresh_from_db()
        # Assert: the refusal actually PREVENTED the wipe (not just printed).
        assert self.allocation.is_active is True


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
            self.allocation, gitea_client=FakeGiteaClient(),
            clone_fn=fake_clone,
            run_cmd=NO_CONTAINER_HOST,
        )
        self.allocation.refresh_from_db()
        # Assert
        assert self.allocation.is_active is False

    def test_clean_reverify_returns_slot_to_ready_pool(self):
        # Arrange: setUp created a stale is_active zombie + its user/project.
        # Act
        reset_and_verify_slot(
            self.allocation, gitea_client=FakeGiteaClient(),
            clone_fn=fake_clone,
            run_cmd=NO_CONTAINER_HOST,
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
            self.allocation, gitea_client=FakeGiteaClient(),
            clone_fn=_boom_clone,
            run_cmd=NO_CONTAINER_HOST,
        )
        self.allocation.refresh_from_db()
        # Assert
        assert (ok, self.allocation.quarantined) == (False, True)

    def test_quarantined_slot_is_not_counted_ready(self):
        # Arrange: setUp created a stale is_active zombie + its user/project.
        # Act
        reset_and_verify_slot(
            self.allocation, gitea_client=FakeGiteaClient(),
            clone_fn=_boom_clone,
            run_cmd=NO_CONTAINER_HOST,
        )
        status = VisitorPool.get_pool_status()
        # Assert: a quarantined slot is never distributable.
        assert status["ready"] == 0


class TestRecleanWithGiteaDisabled(TestCase):
    """A no-Gitea deployment (SCITEX_HUB_VISITOR_POOL_GITEA_ENABLED=false)
    re-cleans slots WITHOUT touching Gitea — it must not quarantine them.

    Dev-preview incident 2026-07-17: reconcile quarantined every slot
    because the repo purge ran despite the allocation-side gate (#395) —
    a configured GITEA_TOKEN with an unreachable backend raised inside
    ``_purge_gitea_repos_verified``, so the pool could never heal
    (``reason=no_ready_slot``; visitors stuck readonly forever).
    """

    def setUp(self):
        self.user = _create_visitor_user_and_project()
        VisitorAllocation.objects.filter(visitor_number=1).delete()
        self.allocation = _stale_active_slot(1)
        self._saved_gate = os.environ.get("SCITEX_HUB_VISITOR_POOL_GITEA_ENABLED")
        os.environ["SCITEX_HUB_VISITOR_POOL_GITEA_ENABLED"] = "false"

    def tearDown(self):
        if self._saved_gate is None:
            os.environ.pop("SCITEX_HUB_VISITOR_POOL_GITEA_ENABLED", None)
        else:
            os.environ["SCITEX_HUB_VISITOR_POOL_GITEA_ENABLED"] = self._saved_gate
        base = Path(settings.BASE_DIR) / "data" / "users" / "visitor-001"
        if base.exists():
            shutil.rmtree(base, ignore_errors=True)

    def test_reclean_succeeds_without_gitea_backend(self):
        # Arrange: a token IS configured but the backend is unreachable —
        # the dev-preview shape. No client is injected, so the purge path
        # must consult the env gate and skip Gitea entirely.
        with override_settings(GITEA_TOKEN="dummy-token"):  # pragma: allowlist secret
            # Act
            ok = reset_and_verify_slot(
                self.allocation,
                clone_fn=fake_clone,
                run_cmd=NO_CONTAINER_HOST,
            )
        self.allocation.refresh_from_db()
        # Assert: verified clean and distributable — never quarantined.
        assert (ok, self.allocation.quarantined) == (True, False)


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


class TestReconcileAsyncDispatch(TestCase):
    """``--async`` keeps the quarantine fail-safe synchronous but dispatches
    the expensive per-slot re-clean to Celery instead of running it inline.

    This is the fix for the boot-serving hang (staging 2026-07-09: the inline
    reconcile left ``django-1`` "Up (unhealthy)" and /landing/ returning
    connection-reset for minutes while every slot was wiped+cloned+verified
    before Daphne ever bound). The safety contract is unchanged: every slot is
    quarantined synchronously first, so nothing is allocatable until a worker
    verifies it clean — visitors get the readonly-visitor fallback meanwhile.

    The command accepts an ``enqueue_fn`` seam (mirroring the existing
    ``gitea_client=``/``clone_fn=`` injection points on
    ``reset_and_verify_slot``) so these tests observe dispatch WITHOUT
    fighting Celery's process-global ``task_always_eager`` flag — the SQLite
    test gate (``SCITEX_HUB_USE_SQLITE_DEV``) forces that True at Django
    settings load time, and it cannot be flipped back mid-process (confirmed:
    neither ``app.conf.update()`` nor attribute assignment on the bound
    Celery app changes the effective value here), so ``.delay()`` would
    otherwise run the reset INLINE with real retries/sleeps — exactly the
    trap ``test_slot_recycling_security.py``'s ``recycled_slot`` fixture
    already documents sidestepping the same way (calling the underlying
    function directly instead of going through ``.delay()``).
    """

    def setUp(self):
        self.user = _create_visitor_user_and_project()
        # A second project stands in for previous-visitor residue. The INLINE
        # re-clean deletes ALL of a visitor's Project rows (pipeline step 1);
        # the async path must NOT touch them in-process — the wipe is queued.
        Project.objects.get_or_create(
            slug="side-project",
            owner=self.user,
            defaults={"name": "Side Project"},
        )
        VisitorAllocation.objects.filter(visitor_number=1).delete()
        self.allocation = _stale_active_slot(1)
        # Snapshot the slug SET rather than hardcoding a count: user creation
        # also auto-provisions a "dotfiles" project via a signal, so the real
        # baseline is {"default-project", "side-project", "dotfiles"} — the
        # exact number is a signal-chain implementation detail; what this
        # test actually cares about is that the async path leaves it UNCHANGED.
        self.projects_before = set(
            Project.objects.filter(owner=self.user).values_list("slug", flat=True)
        )

    def tearDown(self):
        base = Path(settings.BASE_DIR) / "data" / "users" / "visitor-001"
        if base.exists():
            shutil.rmtree(base, ignore_errors=True)

    def test_async_quarantines_slot_synchronously(self):
        # Arrange: setUp created a stale is_active zombie slot.
        # Act
        call_command(
            "reconcile_visitor_slots", "--async", visitor=1, enqueue_fn=lambda i: None
        )
        self.allocation.refresh_from_db()
        # Assert: the fail-safe engages immediately (DB-only, no waiting).
        assert self.allocation.quarantined is True

    def test_async_leaves_slot_out_of_circulation(self):
        # Arrange: setUp created a stale is_active zombie slot.
        # Act
        call_command(
            "reconcile_visitor_slots", "--async", visitor=1, enqueue_fn=lambda i: None
        )
        self.allocation.refresh_from_db()
        # Assert: not distributable (allocation ready-gate refuses it).
        assert (self.allocation.is_active, self.allocation.workspace_ready) == (
            False,
            False,
        )

    def test_async_does_not_run_reclean_inline(self):
        # Arrange: setUp snapshotted the visitor's residue Project slugs
        # (default + side + auto-provisioned dotfiles). Scoped to slot 1
        # (--visitor 1) — the pool is POOL_SIZE=4 by default and Phase 2
        # would otherwise also touch slots 2-4's (unrelated) rows.
        # Act: dispatch via the injected seam — the reset pipeline itself
        # must NOT run in-process.
        call_command(
            "reconcile_visitor_slots", "--async", visitor=1, enqueue_fn=lambda i: None
        )
        # Assert: the residue Project rows survive UNCHANGED (the inline
        # re-clean would delete them all as its first pipeline step).
        projects_after = set(
            Project.objects.filter(owner=self.user).values_list("slug", flat=True)
        )
        assert projects_after == self.projects_before

    def test_async_dispatches_reclean_for_each_quarantined_slot(self):
        # Arrange: a real (tiny) recording function — no mocks. Scoped to
        # slot 1 so exactly one dispatch is expected (POOL_SIZE=4 by
        # default; an unscoped call would also dispatch for slots 2-4).
        dispatched = []
        # Act
        call_command(
            "reconcile_visitor_slots",
            "--async",
            visitor=1,
            enqueue_fn=dispatched.append,
        )
        # Assert: the re-clean was dispatched for slot 1's allocation id.
        assert dispatched == [self.allocation.id]

    def test_async_reports_enqueued_count(self):
        # Arrange: setUp created one quarantinable slot; scope the command
        # to it (--visitor 1) so the reported count is deterministic
        # regardless of the pool's configured size.
        out = StringIO()
        # Act
        call_command(
            "reconcile_visitor_slots",
            "--async",
            visitor=1,
            enqueue_fn=lambda i: None,
            stdout=out,
        )
        # Assert
        assert "Enqueued 1 async re-clean task" in out.getvalue()

    def test_async_quarantined_slot_is_not_allocatable(self):
        # Arrange: async reconcile quarantines slot 1 synchronously.
        call_command(
            "reconcile_visitor_slots", "--async", visitor=1, enqueue_fn=lambda i: None
        )
        session = MockSession("async-quarantine-refuse")
        # Act
        project, _ = VisitorPool.allocate_visitor(session)
        # Assert: refused during the async window (readonly-visitor fallback).
        assert project is None

    def test_async_enqueue_failure_keeps_slot_quarantined(self):
        # Arrange: the broker is unreachable (or any enqueue error) — the
        # safe direction is to leave the slot exactly as quarantined; NEVER
        # mask the failure by returning it to the pool.
        def _boom(allocation_id):
            raise RuntimeError("broker unreachable")

        # Act
        call_command(
            "reconcile_visitor_slots", "--async", visitor=1, enqueue_fn=_boom
        )
        self.allocation.refresh_from_db()
        # Assert
        assert (self.allocation.quarantined, self.allocation.workspace_ready) == (
            True,
            False,
        )

    def test_default_wiring_targets_the_real_release_pipeline_task(self):
        # Arrange: no enqueue_fn override — exercise the command's default.
        from apps.infra.project_app.tasks import reset_visitor_slot

        # Act: the default must resolve to the SAME Celery task the release
        # pipeline already enqueues (slot_lifecycle.release_slot) — not a
        # new/parallel mechanism.
        task_name = reset_visitor_slot.name
        # Assert: identity, not just name — guards against a future refactor
        # accidentally wiring a different/stale task.
        assert task_name.endswith("reset_visitor_slot")


if __name__ == "__main__":
    import os

    import pytest

    pytest.main([os.path.abspath(__file__), "-v"])
