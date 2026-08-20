#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Visitor fail-loud UX tests (card hub-visitor-ux-allapps).

Covers the operator-confirmed 2026-07-07 spec:
- canonical session-role model (anonymous | readonly_visitor | visitor | user)
- readonly downgrade is explained on the next rendered page via the
  header badge/popover — the intrusive downgrade banner was removed
  2026-07-11 (operator 960-965: it dominated the screen, worst on mobile)
- the downgrade reason is STRUCTURED (pool_full | no_ready_slot |
  unknown) and threads through banner / popover / write-rejection copy
  (2026-07-08 iPhone report: popover claimed "pool is full" at 0/16)
- write attempts by readonly visitors get the structured 403
  ({"reason": "readonly-visitor", ...})
- pool occupancy is exposed to templates for the Read-Only badge

Real Django test DB via django.test.TestCase — no mocks.
One assertion per test (STX-TQ007), AAA markers (STX-TQ002).
"""

import json
from datetime import timedelta

from django.contrib.auth.models import AnonymousUser, User
from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone

from apps.infra.project_app.models import VisitorAllocation
from apps.infra.project_app.services.visitor_pool import (
    READONLY_REASON_NO_READY_SLOT,
    READONLY_REASON_POOL_FULL,
    READONLY_REASON_UNKNOWN,
    ROLE_ANONYMOUS,
    ROLE_READONLY_VISITOR,
    ROLE_USER,
    ROLE_VISITOR,
    SESSION_KEY_READONLY_NOTICE,
    SESSION_KEY_READONLY_REASON,
    VisitorPool,
    get_user_role,
)

BROWSER_UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) Safari/605.1"

# Visitor auto-login / readonly-downgrade is triggered by a browser hitting a
# non-skip-listed path. As of card
# hub-landing-page-for-logged-out-visitors-20260727, "/" and "/landing/" are
# EXACT-skipped by VisitorAutoLoginMiddleware so a first-time browser stays
# anonymous on the marketing pages (it must reach /landing/, not the launcher,
# and must not burn a pool slot merely to view marketing). Provisioning — and
# therefore the pool-full → readonly downgrade — now fires at the EXPLICIT
# workspace-entry path the hero "Enter as visitor" CTA points at (/apps/home/,
# not skip-listed). These downgrade tests exercise the trigger there; every
# assertion (readonly login, session markers, banner copy, reason codes) is
# unchanged — only the URL that fires the middleware moved.
ENTRY_PATH = "/apps/home/"


class SessionRoleModelTest(TestCase):
    """get_user_role maps every account shape to exactly one role."""

    def test_anonymous_user_maps_to_anonymous_role(self):
        # Arrange
        user = AnonymousUser()
        # Act
        role = get_user_role(user)
        # Assert
        assert role == ROLE_ANONYMOUS

    def test_readonly_visitor_maps_to_readonly_role(self):
        # Arrange
        user = User.objects.create_user(username="readonly-visitor")
        # Act
        role = get_user_role(user)
        # Assert
        assert role == ROLE_READONLY_VISITOR

    def test_pool_visitor_maps_to_visitor_role(self):
        # Arrange
        user = User.objects.create_user(username="visitor-003")
        # Act
        role = get_user_role(user)
        # Assert
        assert role == ROLE_VISITOR

    def test_registered_account_maps_to_user_role(self):
        # Arrange
        user = User.objects.create_user(username="alice")
        # Act
        role = get_user_role(user)
        # Assert
        assert role == ROLE_USER


class ReadonlyDowngradeExplanationTest(TestCase):
    """Pool-full downgrade explains itself on the next rendered page."""

    @classmethod
    def setUpTestData(cls):
        # Only the shared readonly-visitor exists — no visitor-NNN pool
        # users, so VisitorPool.allocate_visitor() cannot allocate a slot
        # and VisitorAutoLoginMiddleware falls back to readonly-visitor.
        User.objects.create_user(
            username="readonly-visitor",
            password="TestPass123!",  # pragma: allowlist secret
        )

    def test_downgrade_logs_session_in_as_readonly_visitor(self):
        # Arrange — anonymous browser request with an exhausted pool
        # Act
        resp = self.client.get(ENTRY_PATH, HTTP_USER_AGENT=BROWSER_UA)
        # Assert
        assert resp.wsgi_request.user.username == "readonly-visitor"

    def test_downgraded_page_omits_intrusive_readonly_banner(self):
        # Arrange — the big readonly downgrade banner was removed (operator
        # 960-965, 2026-07-11): it dominated the screen — worst on mobile —
        # and hurt onboarding. Readonly state stays discoverable via the
        # header badge/popover (see the reason-threading tests), not a banner.
        # Act — the downgrade request itself is the next rendered page
        resp = self.client.get(ENTRY_PATH, HTTP_USER_AGENT=BROWSER_UA)
        # Assert — the intrusive banner element must stay gone
        assert b"readonly-visitor-banner" not in resp.content

    def test_downgraded_page_explains_slots_preparing_reason(self):
        # Arrange — free slots exist but none is verified clean (this
        # fixture has no visitor-NNN slots at all → no_ready_slot), so
        # the banner must NOT claim the pool is full.
        # Act
        resp = self.client.get(ENTRY_PATH, HTTP_USER_AGENT=BROWSER_UA)
        # Assert
        assert b"Visitor slots are being prepared" in resp.content

    def test_downgraded_page_does_not_claim_pool_full(self):
        # Arrange — 0 busy slots: "pool is full" would be a lie
        # Act
        resp = self.client.get(ENTRY_PATH, HTTP_USER_AGENT=BROWSER_UA)
        # Assert
        assert b"All visitor slots are in use" not in resp.content

    def test_explanation_flag_is_one_shot(self):
        # Arrange — first request consumes the downgrade notice
        self.client.get(ENTRY_PATH, HTTP_USER_AGENT=BROWSER_UA)
        # Act — second page load must not repeat the banner
        resp = self.client.get(ENTRY_PATH, HTTP_USER_AGENT=BROWSER_UA)
        # Assert
        assert b"readonly-visitor-banner" not in resp.content

    def test_downgrade_sets_readonly_session_marker(self):
        # Arrange — anonymous browser request with an exhausted pool
        # Act
        self.client.get(ENTRY_PATH, HTTP_USER_AGENT=BROWSER_UA)
        # Assert
        assert self.client.session.get("is_readonly_visitor") is True


class ReadonlyDowngradeReasonThreadingTest(TestCase):
    """The structured downgrade reason threads through session + copy."""

    @classmethod
    def setUpTestData(cls):
        User.objects.create_user(
            username="readonly-visitor",
            password="TestPass123!",  # pragma: allowlist secret
        )

    def _fill_pool(self):
        """Every slot busy → allocation must record pool_full."""
        expires = timezone.now() + timedelta(hours=1)
        for num in range(1, VisitorPool.POOL_SIZE + 1):
            VisitorAllocation.objects.create(
                visitor_number=num,
                allocation_token=f"tok-{num:03d}",
                expires_at=expires,
                is_active=True,
            )

    def test_no_ready_slot_reason_recorded_in_session(self):
        # Arrange — slots exist in no verified-clean state (none at all)
        # Act
        self.client.get(ENTRY_PATH, HTTP_USER_AGENT=BROWSER_UA)
        # Assert
        assert (
            self.client.session.get(SESSION_KEY_READONLY_REASON)
            == READONLY_REASON_NO_READY_SLOT
        )

    def test_pool_full_reason_recorded_when_all_slots_busy(self):
        # Arrange
        self._fill_pool()
        # Act
        self.client.get(ENTRY_PATH, HTTP_USER_AGENT=BROWSER_UA)
        # Assert
        assert (
            self.client.session.get(SESSION_KEY_READONLY_REASON)
            == READONLY_REASON_POOL_FULL
        )

    def test_pool_full_banner_says_slots_in_use(self):
        # Arrange
        self._fill_pool()
        # Act
        resp = self.client.get(ENTRY_PATH, HTTP_USER_AGENT=BROWSER_UA)
        # Assert
        assert b"All visitor slots are in use" in resp.content

    def test_reason_detail_persists_after_one_shot_banner(self):
        # Arrange — first request consumes the banner notice
        self.client.get(ENTRY_PATH, HTTP_USER_AGENT=BROWSER_UA)
        # Act — the header popover still explains the persistent state
        resp = self.client.get(ENTRY_PATH, HTTP_USER_AGENT=BROWSER_UA)
        # Assert
        assert b"Visitor slots are being prepared" in resp.content

    def test_unrecorded_reason_renders_generic_truthful_copy(self):
        # Arrange — readonly session with NO recorded downgrade reason
        readonly = User.objects.get(username="readonly-visitor")
        self.client.force_login(readonly)
        # Act
        resp = self.client.get("/")
        # Assert — generic truth, never the wrong specific claim
        assert b"No writable visitor slot is available" in resp.content

    def test_unrecorded_reason_never_claims_pool_full(self):
        # Arrange
        readonly = User.objects.get(username="readonly-visitor")
        self.client.force_login(readonly)
        # Act
        resp = self.client.get("/")
        # Assert
        assert b"All visitor slots are in use" not in resp.content


class ReadonlyStructuredWriteRejectionTest(TestCase):
    """Write attempts by readonly visitors get the structured 403."""

    @classmethod
    def setUpTestData(cls):
        cls.readonly_visitor = User.objects.create_user(
            username="readonly-visitor",
            password="TestPass123!",  # pragma: allowlist secret
        )

    def _post_save_file(self, downgrade_reason=None):
        self.client.force_login(self.readonly_visitor)
        if downgrade_reason is not None:
            session = self.client.session
            session[SESSION_KEY_READONLY_REASON] = downgrade_reason
            session.save()
        return self.client.post(
            "/api/workspace/save-file/",
            data=json.dumps({"project_id": 1, "path": "a.txt", "content": "x"}),
            content_type="application/json",
        )

    def test_write_rejection_returns_403(self):
        # Arrange
        # Act
        resp = self._post_save_file()
        # Assert
        assert resp.status_code == 403

    def test_write_rejection_carries_readonly_reason(self):
        # Arrange
        # Act
        resp = self._post_save_file()
        # Assert
        assert resp.json()["reason"] == "readonly-visitor"

    def test_write_rejection_offers_signup_login_retry_actions(self):
        # Arrange
        # Act
        resp = self._post_save_file()
        # Assert
        assert resp.json()["actions"] == ["signup", "login", "retry-later"]

    def test_write_rejection_detail_reflects_preparing_reason(self):
        # Arrange — session recorded no_ready_slot at allocation time
        # Act
        resp = self._post_save_file(downgrade_reason=READONLY_REASON_NO_READY_SLOT)
        # Assert
        assert "Visitor slots are being prepared" in resp.json()["detail"]

    def test_write_rejection_detail_reflects_pool_full_reason(self):
        # Arrange — session recorded pool_full at allocation time
        # Act
        resp = self._post_save_file(downgrade_reason=READONLY_REASON_POOL_FULL)
        # Assert
        assert "All visitor slots are in use" in resp.json()["detail"]

    def test_write_rejection_carries_downgrade_reason_code(self):
        # Arrange
        # Act
        resp = self._post_save_file(downgrade_reason=READONLY_REASON_POOL_FULL)
        # Assert
        assert resp.json()["downgrade_reason"] == READONLY_REASON_POOL_FULL

    def test_write_rejection_without_recorded_reason_is_generic(self):
        # Arrange — no downgrade reason in the session
        # Act
        resp = self._post_save_file()
        # Assert — truthful generic copy, never the wrong specific one
        assert "No writable visitor slot is available" in resp.json()["detail"]

    def test_write_rejection_without_recorded_reason_codes_unknown(self):
        # Arrange
        # Act
        resp = self._post_save_file()
        # Assert
        assert resp.json()["downgrade_reason"] == READONLY_REASON_UNKNOWN


class PoolOccupancyContextTest(TestCase):
    """Pool occupancy is exposed next to the Read-Only badge."""

    @classmethod
    def setUpTestData(cls):
        cls.readonly_visitor = User.objects.create_user(
            username="readonly-visitor",
            password="TestPass123!",  # pragma: allowlist secret
        )

    def setUp(self):
        # The occupancy value is cached for 60s — start each test clean.
        cache.clear()

    def test_readonly_page_context_has_pool_status(self):
        # Arrange
        self.client.force_login(self.readonly_visitor)
        # Act
        resp = self.client.get("/")
        # Assert
        assert resp.context["visitor_pool_status"] is not None

    def test_pool_status_reports_configured_total(self):
        # Arrange
        from apps.infra.project_app.services.visitor_pool import VisitorPool

        self.client.force_login(self.readonly_visitor)
        # Act
        resp = self.client.get("/")
        # Assert
        assert resp.context["visitor_pool_status"]["total"] == VisitorPool.POOL_SIZE

    def test_pool_status_reports_allocated_count(self):
        # Arrange — no allocations exist in this test DB
        self.client.force_login(self.readonly_visitor)
        # Act
        resp = self.client.get("/")
        # Assert
        assert resp.context["visitor_pool_status"]["allocated"] == 0

    def test_readonly_header_shows_visitor_slots_text(self):
        # Arrange
        self.client.force_login(self.readonly_visitor)
        # Act
        resp = self.client.get("/")
        # Assert
        assert b"visitor slots" in resp.content

    def test_regular_user_page_has_no_pool_status(self):
        # Arrange
        regular = User.objects.create_user(
            username="carol",
            password="TestPass123!",  # pragma: allowlist secret
        )
        self.client.force_login(regular)
        # Act
        resp = self.client.get("/")
        # Assert
        assert resp.context["visitor_pool_status"] is None


class SessionRoleExposedToFrontendTest(TestCase):
    """The canonical role is exposed to templates/TS via body data attr."""

    def test_readonly_visitor_body_carries_session_role(self):
        # Arrange
        readonly = User.objects.create_user(
            username="readonly-visitor",
            password="TestPass123!",  # pragma: allowlist secret
        )
        self.client.force_login(readonly)
        # Act
        resp = self.client.get("/")
        # Assert
        assert b'data-session-role="readonly_visitor"' in resp.content

    def test_pool_visitor_body_carries_session_role(self):
        # Arrange
        visitor = User.objects.create_user(
            username="visitor-002",
            password="TestPass123!",  # pragma: allowlist secret
        )
        self.client.force_login(visitor)
        # Act
        resp = self.client.get("/")
        # Assert
        assert b'data-session-role="visitor"' in resp.content

    def test_registered_user_body_carries_session_role(self):
        # Arrange
        user = User.objects.create_user(
            username="dave",
            password="TestPass123!",  # pragma: allowlist secret
        )
        self.client.force_login(user)
        # Act
        resp = self.client.get("/")
        # Assert
        assert b'data-session-role="user"' in resp.content


if __name__ == "__main__":
    import os

    import pytest

    pytest.main([os.path.abspath(__file__)])

# EOF
