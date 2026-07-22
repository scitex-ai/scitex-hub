#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Visitor-slot recycling security tests (visitor-slot isolation audit 2026-07-07).

Invariant under test: only verified-clean slots are redistributed;
failed slots are quarantined.

Run (SQLite, no network/Gitea — the Gitea client and template clone are
injected as tiny real fakes through their seams):

    SCITEX_HUB_DJANGO_SECRET_KEY=local-test-secret \
    SCITEX_HUB_GITEA_SSH_PORT_DEV=2222 \
    SCITEX_HUB_USE_SQLITE_DEV=1 \
    /opt/venv-sac/bin/python -m pytest <abs path to this file>
"""

import shutil
from datetime import timedelta
from pathlib import Path

import pytest
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.sessions.backends.db import SessionStore
from django.core.management import call_command
from django.test import RequestFactory
from django.utils import timezone

from apps.infra.gitea_app.exceptions import GiteaAPIError
from apps.infra.project_app.models import Project, VisitorAllocation
from apps.infra.project_app.services.visitor_pool.pool_manager import PoolAllocator
from apps.infra.project_app.services.visitor_pool.slot_lifecycle import (
    get_or_create_allocation,
    quarantine_slot,
    reset_and_verify_slot,
)
from apps.infra.project_app.services.visitor_pool.workspace_manager import (
    TEMPLATE_MARKER_RELPATH,
    WorkspaceManager,
    WorkspaceResetError,
    verify_template_marker,
)
from apps.infra.project_app.services.visitor_pool.workspace_wipe import (
    WorkspaceWipeError,
    wipe_directory_contents,
)

# ---------------------------------------------------------------------------
# Tiny real fakes (no unittest.mock) injected through the existing seams
# ---------------------------------------------------------------------------


class FakeGiteaClient:
    """In-memory Gitea: repos per owner; list/delete like the real client."""

    def __init__(self, repos_by_owner=None):
        self.repos = {
            owner: list(names) for owner, names in (repos_by_owner or {}).items()
        }
        self.deleted = []

    def list_repositories(self, username):
        return [{"name": name} for name in self.repos.get(username, [])]

    def delete_repository(self, owner, repo):
        if repo in self.repos.get(owner, []):
            self.repos[owner].remove(repo)
        self.deleted.append((owner, repo))
        return True


class FailingDeleteGiteaClient(FakeGiteaClient):
    """Gitea whose repo deletion fails (API error / repo survives)."""

    def delete_repository(self, owner, repo):
        raise GiteaAPIError("boom: cannot delete repository")


class UnreachableGiteaClient:
    """Gitea that cannot be reached at all."""

    def list_repositories(self, username):
        raise GiteaAPIError("Request failed: connection refused")

    def delete_repository(self, owner, repo):
        raise GiteaAPIError("Request failed: connection refused")


def fake_clone(template_id, dest, git_strategy=None):
    """Real (tiny) template clone mirroring the REAL layout.

    The real ``clone_scitex_minimal`` creates dot-prefixed
    ``.scitex/writer/`` (2026-07-08 incident: this fake created
    ``scitex/writer`` — no dot — so the suite stayed green while
    production verification failed on every slot). It MUST build the
    marker path from TEMPLATE_MARKER_RELPATH, which
    test_template_marker_reality.py locks against the real packages.
    """
    manuscript = Path(dest) / TEMPLATE_MARKER_RELPATH / "01_manuscript"
    manuscript.mkdir(parents=True, exist_ok=True)
    (manuscript / "main.tex").write_text("% fresh template\n")
    return True


def failing_clone(template_id, dest, git_strategy=None):
    raise RuntimeError("template clone exploded")


def falsy_clone(template_id, dest, git_strategy=None):
    """Clone that returns False WITHOUT raising — the exact 2026-07-08
    production failure mode (scitex_template swallows the underlying
    ModuleNotFoundError from a broken scitex-writer wheel and returns
    False)."""
    return False


class NoContainerToolchain:
    """run_cmd fake: a host with no SLURM/apptainer binaries installed.

    The container-teardown step treats a missing binary as "nothing to
    tear down" (the dev/CI baseline). Injected through the reset
    pipeline's ``run_cmd`` seam so tests never touch a real cluster.
    """

    def __call__(self, argv, timeout=None):
        raise FileNotFoundError(argv[0])


NO_CONTAINER_HOST = NoContainerToolchain()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _base_path_for(username: str) -> Path:
    """The visitor's ``proj/`` root, under THIS test's private BASE_DIR.

    The ``isolated_visitor_data_root`` autouse fixture in this
    directory's conftest repoints ``settings.BASE_DIR`` at a per-test
    ``tmp_path`` before every test here. That is what makes the
    hardcoded ``visitor-001`` identity below safe under ``pytest-xdist
    -n auto`` — without it, ~128 workers share this one absolute path
    and delete each other's trees mid-reset (CI run 29918531942).
    """
    return Path(settings.BASE_DIR) / "data" / "users" / username / "proj"


def _cleanup_workspace(username: str) -> None:
    base = _base_path_for(username)
    if base.parent.exists():
        shutil.rmtree(base.parent, ignore_errors=True)


@pytest.fixture
def visitor_slot(db):
    """visitor-001 user + allocation row; workspace dirs cleaned afterwards."""
    username = "visitor-001"
    user = User.objects.create(username=username, email=f"{username}@visitor.local")
    allocation = get_or_create_allocation(1)
    yield user, allocation
    _cleanup_workspace(username)


@pytest.fixture
def clean_session(db):
    session = SessionStore()
    session.create()
    return session


def _make_slot_ready(user, allocation, gitea_client=None):
    """Bring a slot to the verified-clean, distributable state."""
    ok = reset_and_verify_slot(
        allocation,
        gitea_client=gitea_client or FakeGiteaClient(),
        clone_fn=fake_clone,
        run_cmd=NO_CONTAINER_HOST,
    )
    if not ok:
        raise RuntimeError("fixture reset must succeed")
    allocation.refresh_from_db()
    return allocation


@pytest.fixture
def ready_slot(visitor_slot):
    user, allocation = visitor_slot
    _make_slot_ready(user, allocation)
    return user, allocation


# ---------------------------------------------------------------------------
# Guarded + verified wipe
# ---------------------------------------------------------------------------


@pytest.fixture
def wiped_readonly_tree(tmp_path):
    """Wipe over the production failure mode: read-only file in read-only dir."""
    base = tmp_path / "proj"
    locked = base / "default-project" / "docs"
    locked.mkdir(parents=True)
    stubborn = locked / "revision.tex"
    stubborn.write_text("previous visitor's manuscript")
    stubborn.chmod(0o400)
    locked.chmod(0o500)
    wipe_directory_contents(base)
    return base


class TestGuardedWipe:
    def test_wipe_recovers_from_readonly_entries(self, wiped_readonly_tree):
        # Arrange
        base = wiped_readonly_tree
        # Act
        residue = list(base.iterdir())
        # Assert
        assert residue == []

    def test_wipe_keeps_the_base_directory_itself(self, wiped_readonly_tree):
        # Arrange
        base = wiped_readonly_tree
        # Act
        still_there = base.exists()
        # Assert
        assert still_there is True

    def test_wipe_target_that_is_a_file_raises(self, tmp_path):
        # Arrange
        target = tmp_path / "not-a-dir"
        target.write_text("x")
        # Act
        # Assert
        with pytest.raises(WorkspaceWipeError):
            wipe_directory_contents(target)

    def test_wipe_of_missing_directory_returns_none(self, tmp_path):
        # Arrange
        missing = tmp_path / "never-existed"
        # Act
        result = wipe_directory_contents(missing)
        # Assert
        assert result is None


# ---------------------------------------------------------------------------
# Reset pipeline: failure → quarantine; quarantined → never allocated
# ---------------------------------------------------------------------------


@pytest.fixture
def clone_failure_reset(visitor_slot):
    user, allocation = visitor_slot
    ok = reset_and_verify_slot(
        allocation,
        gitea_client=FakeGiteaClient(),
        clone_fn=failing_clone,
           run_cmd=NO_CONTAINER_HOST,
    )
    allocation.refresh_from_db()
    return ok, allocation


@pytest.fixture
def falsy_clone_reset(visitor_slot):
    """Reset over the 2026-07-08 prod failure: clone returns falsy."""
    user, allocation = visitor_slot
    ok = reset_and_verify_slot(
        allocation,
        gitea_client=FakeGiteaClient(),
        clone_fn=falsy_clone,
           run_cmd=NO_CONTAINER_HOST,
    )
    allocation.refresh_from_db()
    return ok, allocation


@pytest.fixture
def gitea_delete_failure_reset(visitor_slot):
    user, allocation = visitor_slot
    client = FailingDeleteGiteaClient({"visitor-001": ["default-project"]})
    ok = reset_and_verify_slot(
        allocation,
        gitea_client=client,
        clone_fn=fake_clone,
           run_cmd=NO_CONTAINER_HOST,
    )
    allocation.refresh_from_db()
    return ok, allocation


@pytest.fixture
def unreachable_gitea_reset(visitor_slot):
    user, allocation = visitor_slot
    ok = reset_and_verify_slot(
        allocation,
        gitea_client=UnreachableGiteaClient(),
        clone_fn=fake_clone,
           run_cmd=NO_CONTAINER_HOST,
    )
    allocation.refresh_from_db()
    return ok, allocation


class TestQuarantineOnFailure:
    def test_clone_failure_reset_reports_failure(self, clone_failure_reset):
        # Arrange
        ok, allocation = clone_failure_reset
        # Act
        outcome = ok
        # Assert
        assert outcome is False

    def test_clone_failure_quarantines_slot(self, clone_failure_reset):
        # Arrange
        ok, allocation = clone_failure_reset
        # Act
        quarantined = allocation.quarantined
        # Assert
        assert quarantined is True

    def test_clone_failure_keeps_slot_not_ready(self, clone_failure_reset):
        # Arrange
        ok, allocation = clone_failure_reset
        # Act
        ready = allocation.workspace_ready
        # Assert
        assert ready is False

    def test_clone_failure_records_reason(self, clone_failure_reset):
        # Arrange
        ok, allocation = clone_failure_reset
        # Act
        reason = allocation.quarantine_reason.lower()
        # Assert
        assert "clone" in reason

    def test_falsy_clone_reset_reports_failure(self, falsy_clone_reset):
        # Arrange
        ok, allocation = falsy_clone_reset
        # Act
        outcome = ok
        # Assert
        assert outcome is False

    def test_falsy_clone_quarantines_slot(self, falsy_clone_reset):
        # Arrange
        ok, allocation = falsy_clone_reset
        # Act
        quarantined = allocation.quarantined
        # Assert
        assert quarantined is True

    def test_falsy_clone_keeps_slot_not_ready(self, falsy_clone_reset):
        # Arrange
        ok, allocation = falsy_clone_reset
        # Act
        ready = allocation.workspace_ready
        # Assert
        assert ready is False

    def test_falsy_clone_records_clone_reason(self, falsy_clone_reset):
        # Arrange
        ok, allocation = falsy_clone_reset
        # Act
        reason = allocation.quarantine_reason.lower()
        # Assert
        assert "clone" in reason

    def test_gitea_delete_failure_quarantines_slot(self, gitea_delete_failure_reset):
        # Arrange
        ok, allocation = gitea_delete_failure_reset
        # Act
        quarantined = allocation.quarantined
        # Assert
        assert quarantined is True

    def test_unreachable_gitea_quarantines_slot(self, unreachable_gitea_reset):
        # Arrange
        ok, allocation = unreachable_gitea_reset
        # Act
        quarantined = allocation.quarantined
        # Assert
        assert quarantined is True

    def test_quarantined_slot_is_never_allocated(self, ready_slot, clean_session):
        # Arrange: a quarantined slot even with a perfectly valid workspace
        user, allocation = ready_slot
        quarantine_slot(allocation, "test: pretend the wipe failed")
        # Act
        result = PoolAllocator._try_allocate_slot(1, clean_session, 1)
        # Assert
        assert result == (None, None)

    def test_reset_refuses_to_wipe_active_slot(self, ready_slot):
        # Arrange
        user, allocation = ready_slot
        allocation.is_active = True
        allocation.expires_at = timezone.now() + timedelta(hours=1)
        allocation.save()
        # Act
        ok = reset_and_verify_slot(
            allocation,
            gitea_client=FakeGiteaClient(),
            clone_fn=fake_clone,
            run_cmd=NO_CONTAINER_HOST,
        )
        # Assert
        assert ok is False


# ---------------------------------------------------------------------------
# Ready gate (audit fix #2)
# ---------------------------------------------------------------------------


@pytest.fixture
def sabotaged_marker_allocation(ready_slot, clean_session):
    """DB says ready but the workspace marker was destroyed behind its back."""
    user, allocation = ready_slot
    shutil.rmtree(_base_path_for(user.username) / "default-project" / ".scitex")
    result = PoolAllocator._try_allocate_slot(1, clean_session, 1)
    allocation.refresh_from_db()
    return result, allocation


class TestReadyGate:
    def test_not_ready_slot_is_refused(self, ready_slot, clean_session):
        # Arrange
        user, allocation = ready_slot
        allocation.workspace_ready = False
        allocation.save(update_fields=["workspace_ready"])
        # Act
        result = PoolAllocator._try_allocate_slot(1, clean_session, 1)
        # Assert
        assert result == (None, None)

    def test_rowless_slot_is_refused(self, ready_slot, clean_session):
        # Arrange
        user, allocation = ready_slot
        VisitorAllocation.objects.all().delete()
        # Act
        result = PoolAllocator._try_allocate_slot(1, clean_session, 1)
        # Assert
        assert result == (None, None)

    def test_ready_slot_serves_the_visitor_user(self, ready_slot, clean_session):
        # Arrange
        user, allocation = ready_slot
        # Act
        project, served_user = PoolAllocator._try_allocate_slot(1, clean_session, 1)
        # Assert
        assert served_user == user

    def test_ready_slot_becomes_active_on_allocation(self, ready_slot, clean_session):
        # Arrange
        user, allocation = ready_slot
        # Act
        PoolAllocator._try_allocate_slot(1, clean_session, 1)
        allocation.refresh_from_db()
        # Assert
        assert allocation.is_active is True

    def test_missing_marker_refuses_allocation(self, sabotaged_marker_allocation):
        # Arrange
        result, allocation = sabotaged_marker_allocation
        # Act
        outcome = result
        # Assert
        assert outcome == (None, None)

    def test_missing_marker_quarantines_slot(self, sabotaged_marker_allocation):
        # Arrange
        result, allocation = sabotaged_marker_allocation
        # Act
        quarantined = allocation.quarantined
        # Assert
        assert quarantined is True

    def test_no_ready_slot_sets_readonly_reason_flag(self, ready_slot, clean_session):
        # Arrange
        user, allocation = ready_slot
        allocation.workspace_ready = False
        allocation.save(update_fields=["workspace_ready"])
        # Act
        PoolAllocator.allocate_visitor(clean_session, 1)
        # Assert
        assert (
            clean_session[PoolAllocator.SESSION_KEY_READONLY_REASON] == "no_ready_slot"
        )

    def test_pool_full_sets_pool_full_reason_flag(self, ready_slot, clean_session):
        # Arrange
        user, allocation = ready_slot
        allocation.is_active = True
        allocation.expires_at = timezone.now() + timedelta(hours=1)
        allocation.save()
        # Act
        PoolAllocator.allocate_visitor(clean_session, 1)
        # Assert
        assert clean_session[PoolAllocator.SESSION_KEY_READONLY_REASON] == "pool_full"


# ---------------------------------------------------------------------------
# Release paths: deallocate / expiry middleware / sweep (audit fix #3)
# ---------------------------------------------------------------------------


@pytest.fixture
def deallocated_slot(ready_slot, clean_session):
    user, allocation = ready_slot
    PoolAllocator._try_allocate_slot(1, clean_session, 1)
    PoolAllocator.deallocate_visitor(clean_session)
    allocation.refresh_from_db()
    return allocation, clean_session


@pytest.fixture
def expired_slot_after_middleware(ready_slot, clean_session):
    """Allocate, expire, then run VisitorExpirationMiddleware."""
    from apps.infra.project_app.middleware import VisitorExpirationMiddleware

    user, allocation = ready_slot
    PoolAllocator._try_allocate_slot(1, clean_session, 1)
    allocation.refresh_from_db()
    allocation.expires_at = timezone.now() - timedelta(minutes=5)
    allocation.save(update_fields=["expires_at"])

    request = RequestFactory().get("/writer/")
    request.session = clean_session
    request.user = user
    VisitorExpirationMiddleware(lambda r: None)._sync_body(request)
    allocation.refresh_from_db()
    return allocation, request


@pytest.fixture
def lazily_released_expired_slot(ready_slot, clean_session):
    """An expired-but-never-released slot hit by an allocation attempt."""
    user, allocation = ready_slot
    allocation.is_active = True
    allocation.expires_at = timezone.now() - timedelta(minutes=5)
    allocation.save()
    result = PoolAllocator._try_allocate_slot(1, clean_session, 1)
    allocation.refresh_from_db()
    return result, allocation


@pytest.fixture
def swept_expired_slot(ready_slot):
    from apps.infra.project_app.services.visitor_pool.pool_cleanup import PoolCleanup

    user, allocation = ready_slot
    allocation.is_active = True
    allocation.expires_at = timezone.now() - timedelta(minutes=5)
    allocation.save()
    freed = PoolCleanup.cleanup_expired_allocations()
    allocation.refresh_from_db()
    return freed, allocation


class TestReleasePipeline:
    def test_deallocate_frees_the_slot(self, deallocated_slot):
        # Arrange
        allocation, session = deallocated_slot
        # Act
        active = allocation.is_active
        # Assert
        assert active is False

    def test_deallocate_marks_slot_unready_until_reverified(self, deallocated_slot):
        # Arrange
        allocation, session = deallocated_slot
        # Act
        ready = allocation.workspace_ready
        # Assert
        assert ready is False

    def test_deallocate_pops_session_token(self, deallocated_slot):
        # Arrange
        allocation, session = deallocated_slot
        # Act
        still_present = PoolAllocator.SESSION_KEY_ALLOCATION_TOKEN in session
        # Assert
        assert still_present is False

    def test_expiry_middleware_frees_the_slot(self, expired_slot_after_middleware):
        # Arrange
        allocation, request = expired_slot_after_middleware
        # Act
        active = allocation.is_active
        # Assert
        assert active is False

    def test_expiry_middleware_marks_slot_unready(self, expired_slot_after_middleware):
        # Arrange
        allocation, request = expired_slot_after_middleware
        # Act
        ready = allocation.workspace_ready
        # Assert
        assert ready is False

    def test_expiry_middleware_pops_session_token(self, expired_slot_after_middleware):
        # Arrange
        allocation, request = expired_slot_after_middleware
        # Act
        still_present = (
            PoolAllocator.SESSION_KEY_ALLOCATION_TOKEN in request.session
        )
        # Assert
        assert still_present is False

    def test_expired_unreleased_slot_is_not_served(self, lazily_released_expired_slot):
        # Arrange
        result, allocation = lazily_released_expired_slot
        # Act
        outcome = result
        # Assert
        assert outcome == (None, None)

    def test_expired_unreleased_slot_is_released_lazily(
        self, lazily_released_expired_slot
    ):
        # Arrange
        result, allocation = lazily_released_expired_slot
        # Act
        state = (allocation.is_active, allocation.workspace_ready)
        # Assert
        assert state == (False, False)

    def test_cleanup_sweep_counts_released_slots(self, swept_expired_slot):
        # Arrange
        freed, allocation = swept_expired_slot
        # Act
        count = freed
        # Assert
        assert count == 1

    def test_cleanup_sweep_takes_slot_out_of_circulation(self, swept_expired_slot):
        # Arrange
        freed, allocation = swept_expired_slot
        # Act
        state = (allocation.is_active, allocation.workspace_ready)
        # Assert
        assert state == (False, False)


# ---------------------------------------------------------------------------
# Extended reset scope (audit fix #4)
# ---------------------------------------------------------------------------


@pytest.fixture
def gitea_purge_reset(visitor_slot):
    user, allocation = visitor_slot
    client = FakeGiteaClient({"visitor-001": ["default-project", "leftover-repo"]})
    ok = reset_and_verify_slot(
        allocation,
        gitea_client=client,
        clone_fn=fake_clone,
           run_cmd=NO_CONTAINER_HOST,
    )
    return ok, client


@pytest.fixture
def app_rows_reset(visitor_slot):
    """Reset over a visitor with user-scoped rows from a previous session."""
    from apps.infra.llm_app.models import ChatSession
    from apps.workspace.apps_app.models import (
        AppsModule,
        DevInstallation,
        ModuleInstallation,
        ModuleReview,
        ModuleStar,
    )

    user, allocation = visitor_slot
    module = AppsModule.objects.create(module_name="test-module", author=user)
    ModuleInstallation.objects.create(user=user, module=module)
    ModuleStar.objects.create(user=user, module=module)
    ModuleReview.objects.create(
        user=user, module=module, rating=5, title="left by previous visitor"
    )
    DevInstallation.objects.create(
        user=user,
        source_owner="visitor-001",
        source_repo="default-project",
        module_name="dev__visitor-001__default-project",
    )
    ChatSession.objects.create(user=user)

    ok = reset_and_verify_slot(
        allocation,
        gitea_client=FakeGiteaClient(),
        clone_fn=fake_clone,
           run_cmd=NO_CONTAINER_HOST,
    )
    if not ok:
        raise RuntimeError("fixture reset must succeed")
    return user


class TestExtendedResetScope:
    def test_gitea_purge_reset_succeeds(self, gitea_purge_reset):
        # Arrange
        ok, client = gitea_purge_reset
        # Act
        outcome = ok
        # Assert
        assert outcome is True

    def test_gitea_repos_all_hard_deleted(self, gitea_purge_reset):
        # Arrange
        ok, client = gitea_purge_reset
        # Act
        remaining = client.repos["visitor-001"]
        # Assert
        assert remaining == []

    def test_gitea_leftover_repo_was_explicitly_deleted(self, gitea_purge_reset):
        # Arrange
        ok, client = gitea_purge_reset
        # Act
        deleted = client.deleted
        # Assert
        assert ("visitor-001", "leftover-repo") in deleted

    def test_user_scoped_app_rows_cleared(self, app_rows_reset):
        # Arrange
        from apps.infra.llm_app.models import ChatSession
        from apps.workspace.apps_app.models import (
            DevInstallation,
            ModuleInstallation,
            ModuleReview,
            ModuleStar,
        )

        user = app_rows_reset
        # Act
        leftover_counts = (
            ModuleInstallation.objects.filter(user=user).count(),
            ModuleStar.objects.filter(user=user).count(),
            ModuleReview.objects.filter(user=user).count(),
            DevInstallation.objects.filter(user=user).count(),
            ChatSession.objects.filter(user=user).count(),
        )
        # Assert
        assert leftover_counts == (0, 0, 0, 0, 0)

    def test_reset_deletes_all_visitor_projects_not_just_default(self, ready_slot):
        # Arrange
        user, allocation = ready_slot
        Project.objects.create(
            name="side-project",
            slug="side-project",
            owner=user,
            visibility="private",
            data_location=f"{user.username}/side-project",
        )
        # Act
        reset_and_verify_slot(
            allocation,
            gitea_client=FakeGiteaClient(),
            clone_fn=fake_clone,
            run_cmd=NO_CONTAINER_HOST,
        )
        slugs = list(Project.objects.filter(owner=user).values_list("slug", flat=True))
        # Assert
        assert slugs == ["default-project"]

    def test_no_project_row_survives_a_failed_reset(self, ready_slot):
        """Audit gap #1: no fresh Project row may exist when the reset failed."""
        # Arrange
        user, allocation = ready_slot
        # Act: reset fails BEFORE the create step (unreachable Gitea)
        reset_and_verify_slot(
            allocation,
            gitea_client=UnreachableGiteaClient(),
            clone_fn=fake_clone,
            run_cmd=NO_CONTAINER_HOST,
        )
        # Assert
        assert Project.objects.filter(owner=user).exists() is False


# ---------------------------------------------------------------------------
# Boot reconciliation (operator msg 606/607)
# ---------------------------------------------------------------------------


@pytest.fixture
def boot_reconciled_states(db, clean_session):
    """Slots in every pre-restart state, after `reconcile_visitor_slots
    --quarantine-only`."""
    for number in (1, 2, 3):
        username = f"visitor-{number:03d}"
        User.objects.create(username=username, email=f"{username}@visitor.local")
    alloc_active = get_or_create_allocation(1)  # allocated at shutdown
    alloc_active.is_active = True
    alloc_active.expires_at = timezone.now() + timedelta(hours=1)
    alloc_active.workspace_ready = True
    alloc_active.save()
    alloc_resetting = get_or_create_allocation(2)  # mid-reset at shutdown
    alloc_resetting.is_active = False
    alloc_resetting.workspace_ready = False
    alloc_resetting.save()
    alloc_idle = get_or_create_allocation(3)  # idle-verified before shutdown
    alloc_idle.is_active = False
    alloc_idle.workspace_ready = True
    alloc_idle.save()

    call_command("reconcile_visitor_slots", "--quarantine-only")

    allocations = (alloc_active, alloc_resetting, alloc_idle)
    for allocation in allocations:
        allocation.refresh_from_db()
    yield allocations, clean_session
    for number in (1, 2, 3):
        _cleanup_workspace(f"visitor-{number:03d}")


class TestBootReconciliation:
    def test_all_unverified_states_are_quarantined(self, boot_reconciled_states):
        # Arrange
        allocations, session = boot_reconciled_states
        # Act
        flags = tuple(a.quarantined for a in allocations)
        # Assert
        assert flags == (True, True, True)

    def test_all_slots_are_out_of_circulation(self, boot_reconciled_states):
        # Arrange
        allocations, session = boot_reconciled_states
        # Act
        flags = tuple((a.is_active, a.workspace_ready) for a in allocations)
        # Assert
        assert flags == ((False, False), (False, False), (False, False))

    def test_quarantined_pool_serves_nobody(self, boot_reconciled_states):
        # Arrange
        allocations, session = boot_reconciled_states
        # Act
        result = PoolAllocator.allocate_visitor(session, 3)
        # Assert
        assert result == (None, None)

    def test_quarantined_pool_reports_no_ready_slot_reason(
        self, boot_reconciled_states
    ):
        # Arrange
        allocations, session = boot_reconciled_states
        # Act
        PoolAllocator.allocate_visitor(session, 3)
        # Assert
        assert session[PoolAllocator.SESSION_KEY_READONLY_REASON] == "no_ready_slot"

    def test_quarantined_slot_returns_after_verified_reclean(
        self, visitor_slot, clean_session
    ):
        # Arrange
        user, allocation = visitor_slot
        quarantine_slot(allocation, "boot-reconcile: test")
        # Act
        reset_and_verify_slot(
            allocation,
            gitea_client=FakeGiteaClient(),
            clone_fn=fake_clone,
            run_cmd=NO_CONTAINER_HOST,
        )
        project, served_user = PoolAllocator._try_allocate_slot(1, clean_session, 1)
        # Assert
        assert served_user == user


# ---------------------------------------------------------------------------
# End-to-end recycle: allocate → write residue → expire → re-allocate
# ---------------------------------------------------------------------------


@pytest.fixture
def recycled_slot(ready_slot, clean_session):
    """Full recycle: visitor A leaves residue, expires, slot re-verified,
    visitor B allocates. Returns observations for single-assert tests."""
    from apps.infra.llm_app.models import ChatSession
    from apps.infra.project_app.middleware import VisitorExpirationMiddleware

    user, allocation = ready_slot
    gitea = FakeGiteaClient({"visitor-001": []})

    # Visitor A allocates and leaves residue: files (incl. the read-only
    # production wipe-killer), a stray file outside the project, a chat
    # session, and a pushed Gitea repo.
    PoolAllocator._try_allocate_slot(1, clean_session, 1)
    workspace = _base_path_for(user.username) / "default-project"
    secret = workspace / "docs" / "secret-notes.txt"
    secret.parent.mkdir(parents=True, exist_ok=True)
    secret.write_text("visitor A's private research idea")
    secret.chmod(0o400)
    stray = _base_path_for(user.username) / "outside-project.txt"
    stray.write_text("file outside the default project")
    gitea.repos["visitor-001"] = ["default-project"]
    ChatSession.objects.create(user=user)

    # Session expires; the middleware runs the release pipeline.
    allocation.refresh_from_db()
    allocation.expires_at = timezone.now() - timedelta(minutes=1)
    allocation.save(update_fields=["expires_at"])
    request = RequestFactory().get("/writer/")
    request.session = clean_session
    request.user = user
    VisitorExpirationMiddleware(lambda r: None)._sync_body(request)
    allocation.refresh_from_db()

    # While the async reset is pending (Celery down scenario) the slot
    # must not be servable.
    session_b = SessionStore()
    session_b.create()
    pending_alloc = PoolAllocator._try_allocate_slot(1, session_b, 1)

    # The async reset runs (same code path as the Celery task body,
    # executed synchronously with the injected fakes).
    reset_ok = reset_and_verify_slot(
        allocation,
        gitea_client=gitea,
        clone_fn=fake_clone,
           run_cmd=NO_CONTAINER_HOST,
    )

    # Visitor B allocates the recycled slot.
    project_b, user_b = PoolAllocator._try_allocate_slot(1, session_b, 1)

    return {
        "user": user,
        "user_b": user_b,
        "pending_alloc": pending_alloc,
        "reset_ok": reset_ok,
        "secret": secret,
        "stray": stray,
        "workspace": workspace,
        "base_entries": {p.name for p in _base_path_for(user.username).iterdir()},
        "gitea": gitea,
    }


class TestRecycleEndToEnd:
    def test_slot_is_not_served_while_reset_pending(self, recycled_slot):
        # Arrange
        obs = recycled_slot
        # Act
        pending = obs["pending_alloc"]
        # Assert
        assert pending == (None, None)

    def test_reset_verifies_clean(self, recycled_slot):
        # Arrange
        obs = recycled_slot
        # Act
        ok = obs["reset_ok"]
        # Assert
        assert ok is True

    def test_recycled_slot_serves_next_visitor(self, recycled_slot):
        # Arrange
        obs = recycled_slot
        # Act
        user_b = obs["user_b"]
        # Assert
        assert user_b == obs["user"]

    def test_zero_filesystem_residue_after_recycle(self, recycled_slot):
        # Arrange
        obs = recycled_slot
        # Act
        residue_state = (
            obs["secret"].exists(),
            obs["stray"].exists(),
            obs["base_entries"],
        )
        # Assert
        # The widened reset wipes the whole home root, then recreates
        # proj/ via the same skeleton path terminal spawns use — so a
        # fresh dotfiles repo + workspace metadata are EXPECTED next to
        # the re-cloned project.
        assert residue_state == (
            False,
            False,
            {"default-project", "dotfiles", "workspace_info.json"},
        )

    def test_recycled_workspace_has_fresh_template_marker(self, recycled_slot):
        # Arrange
        obs = recycled_slot
        # Act
        marker_ok = verify_template_marker(obs["workspace"])
        # Assert
        assert marker_ok is True

    def test_chat_rows_do_not_survive_recycle(self, recycled_slot):
        # Arrange
        from apps.infra.llm_app.models import ChatSession

        obs = recycled_slot
        # Act
        chat_count = ChatSession.objects.filter(user=obs["user"]).count()
        # Assert
        assert chat_count == 0

    def test_gitea_repos_do_not_survive_recycle(self, recycled_slot):
        # Arrange
        obs = recycled_slot
        # Act
        remaining = obs["gitea"].repos["visitor-001"]
        # Assert
        assert remaining == []

    def test_exactly_one_fresh_project_row_after_recycle(self, recycled_slot):
        # Arrange
        obs = recycled_slot
        # Act
        row_count = Project.objects.filter(owner=obs["user"]).count()
        # Assert
        assert row_count == 1


# ---------------------------------------------------------------------------
# Direct pipeline check (audit gap #1 regression guard)
# ---------------------------------------------------------------------------


class TestResetPipelineFailLoud:
    def test_reset_raises_loud_instead_of_swallowing(self, visitor_slot):
        # Arrange
        user, allocation = visitor_slot
        # Act
        # Assert
        with pytest.raises(WorkspaceResetError):
            WorkspaceManager.reset_visitor_workspace(
                user,
                gitea_client=FakeGiteaClient(),
                clone_fn=failing_clone,
                run_cmd=NO_CONTAINER_HOST,
            )


if __name__ == "__main__":
    import os

    pytest.main([os.path.abspath(__file__)])
