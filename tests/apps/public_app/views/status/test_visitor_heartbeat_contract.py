#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The heartbeat contract the visitor countdown is now keyed to.

WHY THIS FILE EXISTS. A prospective customer clicked "Enter as visitor", read
for about two minutes, and the browser navigated itself to /visitor-expired/
claiming the 60-minute session had ended -- while the header badge on that same
page still showed 58:10 and this endpoint was reporting remaining_seconds=3599.

The client had captured its deadline ONCE, at render time, from
``visitor_expires_at`` -- which at first render is the PROBATION stamp
(``PoolAllocator.PROBATION_SECONDS = 120``), never the session lease. The fix
makes the countdown re-read ``expires_at`` from every heartbeat response and
evict ONLY on a server-declared expiry. Both halves rest on facts about THIS
view, so both facts are pinned here:

  1. A live allocation answers 200 with ``status="active"`` and an
     ``expires_at`` that the beat has just EXTENDED past probation. This is the
     value the countdown now trusts; if it stopped being emitted, or stopped
     being extended, the countdown would silently fall back to a stale stamp
     and the eviction bug returns.

  2. A gone allocation answers 404 with ``status="expired"``. That response is
     the ONLY thing permitted to evict a visitor. If it stopped being a 404 the
     client would never leave a dead session -- which is the failure mode a
     careless "just delete the redirect" fix produces.

DO NOT REMOVE OR SHORTEN PROBATION TO MAKE ANY OF THIS SIMPLER.
``PROBATION_SECONDS`` is deliberate anti-crawler defence added after the
2026-07-14 slot-squatting incident, where a JS-less crawler held all 16 slots
for an hour each and every human was served read-only. Probation was never the
bug; the client treating the probation stamp as the session deadline was.

The client half of this contract is covered by
tests/ts/shared/components/visitor-countdown.test.ts.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta

import pytest
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone

from apps.infra.project_app.models import VisitorAllocation
from apps.infra.project_app.services.visitor_pool import VisitorPool
from apps.infra.project_app.services.visitor_pool.pool_manager import PoolAllocator

HEARTBEAT_URL = reverse("public_app:visitor_heartbeat_api")


@pytest.fixture
def probation_allocation(db):
    """A freshly allocated visitor holding a 120s PROBATION lease.

    This is the exact state the browser is in when the header HTML is
    rendered, which is why the render-time attribute can never be the session
    deadline.
    """
    user, _ = User.objects.get_or_create(
        username="visitor-001", defaults={"email": "v001@example.com"}
    )
    VisitorAllocation.objects.filter(visitor_number=1).delete()
    allocation = VisitorAllocation.objects.create(
        visitor_number=1,
        session_key="heartbeat-contract-session",
        allocation_token=secrets.token_hex(32),
        expires_at=timezone.now() + timedelta(seconds=PoolAllocator.PROBATION_SECONDS),
        is_active=True,
        workspace_ready=True,
    )
    return user, allocation


@pytest.fixture
def visitor_client(client, probation_allocation):
    """A Django client logged in as that visitor, carrying its allocation token."""
    user, allocation = probation_allocation
    client.force_login(user)
    session = client.session
    session[VisitorPool.SESSION_KEY_ALLOCATION_TOKEN] = allocation.allocation_token
    session.save()
    return client


@pytest.fixture
def released_visitor_client(visitor_client, probation_allocation):
    """The same visitor after the reaper released the slot (is_active=False)."""
    _user, allocation = probation_allocation
    VisitorAllocation.objects.filter(pk=allocation.pk).update(is_active=False)
    return visitor_client


class TestHeartbeatPublishesTheRealLease:
    """Half one of the fix: the countdown's deadline must come from here."""

    def test_a_live_visitor_gets_http_200(self, visitor_client):
        # Arrange
        url = HEARTBEAT_URL
        # Act
        response = visitor_client.get(url)
        # Assert
        assert response.status_code == 200

    def test_a_live_visitor_is_reported_active(self, visitor_client):
        # Arrange
        url = HEARTBEAT_URL
        # Act
        payload = visitor_client.get(url).json()
        # Assert
        assert payload["status"] == "active"

    def test_the_response_carries_expires_at(self, visitor_client):
        # Arrange -- the field the countdown now reads on every beat; without
        # it the client has nothing but the stale render-time stamp.
        url = HEARTBEAT_URL
        # Act
        payload = visitor_client.get(url).json()
        # Assert
        assert "expires_at" in payload

    def test_expires_at_is_in_the_future(self, visitor_client):
        # Arrange
        url = HEARTBEAT_URL
        # Act
        payload = visitor_client.get(url).json()
        # Assert
        assert datetime.fromisoformat(payload["expires_at"]) > timezone.now()

    def test_the_beat_extends_the_lease_past_probation(self, visitor_client):
        # Arrange -- this is the number that made the whole bug visible: the
        # page was rendered claiming ~120s while the real lease was an hour.
        url = HEARTBEAT_URL
        # Act
        payload = visitor_client.get(url).json()
        # Assert
        assert payload["remaining_seconds"] > PoolAllocator.PROBATION_SECONDS

    def test_expires_at_overtakes_the_render_time_stamp(
        self, visitor_client, probation_allocation
    ):
        # Arrange
        _user, allocation = probation_allocation
        rendered_stamp = allocation.expires_at
        # Act
        payload = visitor_client.get(HEARTBEAT_URL).json()
        # Assert
        assert datetime.fromisoformat(payload["expires_at"]) > rendered_stamp

    def test_the_render_time_stamp_really_was_the_shorter_one(
        self, probation_allocation
    ):
        # Arrange -- a negative control for the two rows above. If allocation
        # ever started handing out the full session at render time, "extends
        # past probation" would pass vacuously and prove nothing.
        _user, allocation = probation_allocation
        # Act
        rendered_seconds = (allocation.expires_at - timezone.now()).total_seconds()
        # Assert
        assert rendered_seconds <= PoolAllocator.PROBATION_SECONDS


class TestHeartbeatStillDeclaresGenuineExpiry:
    """Half two: the ONE signal that may evict a visitor must still exist.

    This is the row a careless fix fails. Removing the client's navigation
    satisfies every "does not redirect" assertion; it also strands a visitor on
    a dead session forever. The eviction has to survive -- it just has to be
    the SERVER's call.
    """

    def test_a_released_allocation_answers_404(self, released_visitor_client):
        # Arrange -- visitor-heartbeat.ts keys its eviction off 404/401/403.
        url = HEARTBEAT_URL
        # Act
        response = released_visitor_client.get(url)
        # Assert
        assert response.status_code == 404

    def test_the_404_body_says_expired(self, released_visitor_client):
        # Arrange
        url = HEARTBEAT_URL
        # Act
        payload = released_visitor_client.get(url).json()
        # Assert
        assert payload["status"] == "expired"

    def test_an_unauthenticated_caller_gets_401(self, client, db):
        # Arrange -- the other eviction-worthy status: the visitor login is
        # gone entirely.
        url = HEARTBEAT_URL
        # Act
        response = client.get(url)
        # Assert
        assert response.status_code == 401


if __name__ == "__main__":
    import os

    pytest.main([os.path.abspath(__file__)])
