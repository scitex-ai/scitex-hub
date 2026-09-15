"""Transaction controls for retained visitor-slot reset machinery."""

import threading
import time

import pytest
from django.contrib.auth.models import User
from django.db import close_old_connections
from django.utils import timezone

from apps.infra.project_app.models import Project, VisitorAllocation
from apps.infra.project_app.services.visitor_pool import slot_lifecycle
from apps.infra.project_app.services.visitor_pool.workspace_manager import (
    WorkspaceManager,
)


@pytest.fixture
def reset_slot():
    user = User.objects.create_user(username="visitor-001")
    project = Project.objects.create(
        owner=user,
        slug="default-project",
        name="Handwritten Digits (Example)",
        description="fixture",
    )
    allocation = VisitorAllocation.objects.create(
        visitor_number=1,
        session_key="",
        allocation_token="fixture-token",
        expires_at=timezone.now(),
        is_active=False,
        workspace_ready=False,
    )
    return user, project, allocation


@pytest.mark.django_db(transaction=True)
def test_concurrent_resets_are_serialized_per_slot(monkeypatch, reset_slot):
    """Two creator paths may not concurrently wipe/create one slot."""
    _user, _project, allocation = reset_slot
    entered = 0
    maximum_entered = 0
    guard = threading.Lock()
    first_entered = threading.Event()
    release_first = threading.Event()
    second_started = threading.Event()
    results = []

    def controlled_reset(cls, user, **kwargs):
        nonlocal entered, maximum_entered
        with guard:
            entered += 1
            maximum_entered = max(maximum_entered, entered)
            ordinal = entered
        if ordinal == 1:
            first_entered.set()
            assert release_first.wait(5)
        with guard:
            entered -= 1

    monkeypatch.setattr(
        WorkspaceManager,
        "reset_visitor_workspace",
        classmethod(controlled_reset),
    )

    def run(mark_started=None):
        close_old_connections()
        if mark_started:
            mark_started.set()
        row = VisitorAllocation.objects.get(pk=allocation.pk)
        results.append(slot_lifecycle.reset_and_verify_slot(row))
        close_old_connections()

    first = threading.Thread(target=run)
    second = threading.Thread(target=run, args=(second_started,))
    first.start()
    assert first_entered.wait(5)
    second.start()
    assert second_started.wait(5)
    time.sleep(0.2)
    release_first.set()
    first.join(5)
    second.join(5)

    assert results == [True, True]
    assert maximum_entered == 1


@pytest.mark.django_db(transaction=True)
def test_failed_reset_rolls_back_project_deletion(monkeypatch, reset_slot):
    """A transient creator failure preserves the last DB-consistent project."""
    user, project, allocation = reset_slot

    def delete_then_fail(cls, visitor_user, **kwargs):
        Project.objects.filter(owner=visitor_user).delete()
        raise RuntimeError("injected transient creator failure")

    monkeypatch.setattr(
        WorkspaceManager,
        "reset_visitor_workspace",
        classmethod(delete_then_fail),
    )

    assert slot_lifecycle.reset_and_verify_slot(allocation) is False
    assert Project.objects.filter(pk=project.pk, owner=user).exists()
    allocation.refresh_from_db()
    assert allocation.quarantined is True
    assert "transient creator failure" in allocation.quarantine_reason
