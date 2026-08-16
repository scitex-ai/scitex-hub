#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A visitor slot must record WHO holds it, or it can never be released.

THE DEFECT, measured on production 2026-08-16 by driving the live site with
a real browser. Every active visitor allocation was ownerless:

    ACTIVE 002 session_key='' token=6fb4f9b166...
    ACTIVE 014 session_key='' token=510cbb64ff...
    ACTIVE 013 session_key='' token=07e5c9e135...
    ...
    DISTINCT_SESSION_KEYS_AMONG_ACTIVE = {'(empty)': 11}

Eleven of eleven. The line was:

    allocation.session_key = session.session_key or ""

A brand-new Django session has NO session_key until it has been persisted —
the key is assigned on first save. The middleware allocates before that, so
``session.session_key`` is None and the ``or ""`` silently turns "there is
no owner yet" into "the owner is the empty string", then stores the row.

WHAT THAT ONE COERCION COST. ``deallocate_visitor()`` matches on the
session, so an ownerless row can never be released; it survives only until
the 120-second probation lease expires. Meanwhile the visitor is served the
shared ``readonly-visitor`` account, so the heartbeat that would promote the
lease is never sent (the endpoint rejects any username outside visitor-NNN).
Every navigation burned fresh slots and handed the visitor the shared
account. Measured: ONE /enter/ took the pool from allocated=12/ready=3 to
allocated=14/ready=1 and still returned read-only. Sixteen slots survive
about eight page loads. That shared account is the one that accumulated
seventeen other people's chat sessions.

WHY IT WAS INVISIBLE FOR SO LONG, and this is the part worth keeping. The
existing suite drives the allocator with a hand-written stand-in:

    class MockSession(dict):
        def __init__(self, session_key="test-session-key"):
            ...
        def save(self):
            pass

It ALWAYS has a session_key, and its save() is a no-op. So the ``or ""``
branch is unreachable in every existing test — the double encodes the
author's assumption (sessions arrive with keys) and can therefore only ever
confirm it. The tests were not weak; they were testing a different object
from the one production uses. That is why this file uses the REAL
``django.contrib.sessions.backends.db.SessionStore``: it is the only way to
observe the state production actually passes in.

WHAT THIS GUARDS: that an allocation handed to a visitor identifies its
holder. Not the mechanism — ``session.create()`` versus ``save()`` is an
implementation detail — only that the row is never ownerless.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.sessions.backends.db import SessionStore
from django.test import TestCase
from django.utils import timezone

from apps.infra.project_app.models import Project, VisitorAllocation
from apps.infra.project_app.services.project_filesystem import (
    get_project_filesystem_manager,
)
from apps.infra.project_app.services.visitor_pool import VisitorPool
from apps.infra.project_app.services.visitor_pool.workspace_manager import (
    TEMPLATE_MARKER_RELPATH,
)


class VisitorAllocationKnowsItsOwnerTest(TestCase):
    """Drive the allocator with the session type production actually uses."""

    def setUp(self):
        self.user, _ = User.objects.get_or_create(
            username="visitor-001", defaults={"email": "v001@example.com"}
        )
        self.project, _ = Project.objects.get_or_create(
            slug="default-project",
            owner=self.user,
            defaults={"name": "Default Project"},
        )
        VisitorAllocation.objects.filter(visitor_number=1).delete()
        VisitorAllocation.objects.create(
            visitor_number=1,
            session_key="",
            allocation_token="",
            expires_at=timezone.now(),
            is_active=False,
            workspace_ready=True,
            quarantined=False,
        )
        # The synchronous pre-handoff check refuses a slot without the
        # template marker, so without this every allocation below is a
        # vacuous None and the assertions prove nothing.
        manager = get_project_filesystem_manager(self.user)
        marker = Path(manager.base_path) / self.project.slug / TEMPLATE_MARKER_RELPATH
        marker.mkdir(parents=True, exist_ok=True)
        (marker / "config.yaml").write_text("template: true\n")

    def tearDown(self):
        base = Path(settings.BASE_DIR) / "data" / "users" / "visitor-001"
        if base.exists():
            shutil.rmtree(base, ignore_errors=True)

    def test_a_fresh_session_really_has_no_key(self):
        """The premise. If Django ever changes this, the guard below is moot."""
        # Arrange
        session = SessionStore()

        # Act
        key = session.session_key

        # Assert
        assert key is None, (
            "a brand-new SessionStore is expected to have no key until saved; "
            "if this changed, revisit the allocator's ownership handling"
        )

    def test_a_clean_ready_slot_is_actually_handed_out(self):
        """Vacuity check: if handoff fails, everything below is trivially true."""
        # Arrange
        session = SessionStore()

        # Act
        project, _ = VisitorPool.allocate_visitor(session)

        # Assert
        assert project is not None, "no slot was served — the rest is vacuous"

    @pytest.mark.guards(
        defect=(
            "allocate stored `session.session_key or \"\"` for a not-yet-saved "
            "session, so every active visitor allocation was ownerless and "
            "deallocate_visitor could never release it"
        )
    )
    def test_allocation_records_a_real_session_key(self):
        # Arrange
        session = SessionStore()

        # Act
        VisitorPool.allocate_visitor(session)
        allocation = VisitorAllocation.objects.get(visitor_number=1)

        # Assert
        assert allocation.session_key, (
            "the allocation was stored with an empty session_key — it is "
            "ownerless and can never be released by deallocate_visitor()"
        )

    @pytest.mark.guards(
        defect=(
            "an ownerless allocation cannot be matched back to the browser "
            "holding it, so a returning visitor allocated a second slot "
            "instead of reusing their own"
        )
    )
    def test_the_recorded_owner_is_the_session_that_asked(self):
        # Arrange
        session = SessionStore()

        # Act
        VisitorPool.allocate_visitor(session)
        allocation = VisitorAllocation.objects.get(visitor_number=1)

        # Assert
        assert allocation.session_key == session.session_key

    def test_no_active_allocation_is_ever_ownerless(self):
        """The invariant, stated as production would check it."""
        # Arrange
        session = SessionStore()

        # Act
        VisitorPool.allocate_visitor(session)
        ownerless = VisitorAllocation.objects.filter(
            is_active=True, session_key=""
        ).count()

        # Assert
        assert ownerless == 0, (
            f"{ownerless} active allocation(s) have no session_key; on "
            "production this was 11 of 11"
        )
