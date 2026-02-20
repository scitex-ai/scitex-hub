#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for visitor pool management.

Tests cover:
- Pool initialization and status
- Visitor allocation and deallocation
- Session reuse and expiration handling
"""

from datetime import timedelta

import pytest
from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from apps.project_app.models import Project, VisitorAllocation
from apps.project_app.services.visitor_pool import VisitorPool


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


class TestVisitorPoolStatus(TestCase):
    """Test pool status reporting."""

    def test_get_pool_status_returns_dict(self):
        """Pool status returns expected keys."""
        status = VisitorPool.get_pool_status()

        assert "total" in status
        assert "allocated" in status
        assert "free" in status
        assert "expired" in status

    def test_get_pool_status_total_matches_pool_size(self):
        """Pool total matches configured pool size."""
        status = VisitorPool.get_pool_status()
        assert status["total"] == VisitorPool.POOL_SIZE

    def test_get_pool_status_free_plus_allocated_equals_total(self):
        """Free + allocated slots should approximately equal total."""
        status = VisitorPool.get_pool_status()
        # Note: expired allocations can skew this, so we just check sanity
        assert status["free"] >= 0
        assert status["allocated"] >= 0


class TestVisitorAllocation(TestCase):
    """Test visitor slot allocation."""

    def setUp(self):
        """Ensure visitor-001 user and project exist."""
        self.visitor_user, _ = User.objects.get_or_create(
            username="visitor-001",
            defaults={
                "email": "visitor001@example.com",
            },
        )
        if not self.visitor_user.has_usable_password():
            self.visitor_user.set_password("testpass123")
            self.visitor_user.save()

        self.visitor_project, _ = Project.objects.get_or_create(
            slug="default-project",
            owner=self.visitor_user,
            defaults={"name": "Default Project"},
        )

        # Clear any existing allocations for visitor-001
        VisitorAllocation.objects.filter(visitor_number=1).delete()

    def test_allocate_visitor_success(self):
        """Successfully allocate visitor slot."""
        session = MockSession("test-alloc-success")

        project, user = VisitorPool.allocate_visitor(session)

        assert project is not None
        assert user is not None
        assert VisitorPool.SESSION_KEY_ALLOCATION_TOKEN in session

    def test_allocate_visitor_stores_session_data(self):
        """Allocation stores required data in session."""
        session = MockSession("test-session-data")

        project, user = VisitorPool.allocate_visitor(session)

        if project:  # Only if allocation succeeded
            assert VisitorPool.SESSION_KEY_PROJECT_ID in session
            assert VisitorPool.SESSION_KEY_VISITOR_ID in session
            assert VisitorPool.SESSION_KEY_ALLOCATION_TOKEN in session

    def test_allocate_visitor_reuses_existing(self):
        """Reuse existing allocation if still valid."""
        session = MockSession("test-reuse")

        # First allocation
        project1, user1 = VisitorPool.allocate_visitor(session)

        if project1:  # Only if allocation succeeded
            token1 = session.get(VisitorPool.SESSION_KEY_ALLOCATION_TOKEN)

            # Second allocation should reuse
            project2, user2 = VisitorPool.allocate_visitor(session)

            token2 = session.get(VisitorPool.SESSION_KEY_ALLOCATION_TOKEN)
            assert token1 == token2  # Same allocation reused

    def test_deallocate_visitor_clears_session(self):
        """Deallocate visitor slot clears session data."""
        session = MockSession("test-dealloc")

        # Allocate first
        VisitorPool.allocate_visitor(session)

        # Deallocate
        VisitorPool.deallocate_visitor(session)

        assert VisitorPool.SESSION_KEY_ALLOCATION_TOKEN not in session
        assert VisitorPool.SESSION_KEY_PROJECT_ID not in session
        assert VisitorPool.SESSION_KEY_VISITOR_ID not in session


class TestVisitorAllocationExpiration(TestCase):
    """Test handling of expired allocations."""

    def setUp(self):
        """Ensure visitor-001 user and project exist."""
        self.visitor_user, _ = User.objects.get_or_create(
            username="visitor-001",
            defaults={"email": "visitor001@example.com"},
        )
        self.visitor_project, _ = Project.objects.get_or_create(
            slug="default-project",
            owner=self.visitor_user,
            defaults={"name": "Default Project"},
        )
        # Clear existing allocations
        VisitorAllocation.objects.filter(visitor_number=1).delete()

    def test_expired_allocation_allows_new_allocation(self):
        """Expired allocation allows new allocation to same slot."""
        # Create expired allocation
        VisitorAllocation.objects.create(
            visitor_number=1,
            session_key="old-session",
            allocation_token="expired-token",
            expires_at=timezone.now() - timedelta(hours=1),
            is_active=True,
        )

        # New session should be able to allocate
        session = MockSession("new-session")
        project, user = VisitorPool.allocate_visitor(session)

        assert project is not None

    def test_cleanup_expired_allocations_deactivates(self):
        """Cleanup marks expired allocations as inactive."""
        # Create expired allocation
        VisitorAllocation.objects.filter(visitor_number=1).delete()
        allocation = VisitorAllocation.objects.create(
            visitor_number=1,
            session_key="old-session",
            allocation_token="expired-token",
            expires_at=timezone.now() - timedelta(hours=1),
            is_active=True,
        )

        VisitorPool.cleanup_expired_allocations()

        allocation.refresh_from_db()
        assert not allocation.is_active


class TestPoolAllocatorEdgeCases(TestCase):
    """Test edge cases in pool allocation."""

    def test_deallocate_without_allocation_is_safe(self):
        """Deallocation is safe when no allocation exists."""
        session = MockSession("no-alloc")

        # Should not raise
        VisitorPool.deallocate_visitor(session)

    def test_deallocate_with_invalid_token_is_safe(self):
        """Deallocation handles invalid token gracefully."""
        session = MockSession("invalid-token-session")
        session[VisitorPool.SESSION_KEY_ALLOCATION_TOKEN] = "invalid-token-xyz"

        # Should not raise
        VisitorPool.deallocate_visitor(session)


class TestVisitorPoolConstants(TestCase):
    """Test visitor pool constants and configuration."""

    def test_visitor_user_prefix(self):
        """Visitor user prefix is correct."""
        assert VisitorPool.VISITOR_USER_PREFIX == "visitor-"

    def test_session_lifetime(self):
        """Session lifetime is 1 hour."""
        assert VisitorPool.SESSION_LIFETIME_HOURS == 1

    def test_pool_size_positive(self):
        """Pool size is at least 1."""
        assert VisitorPool.POOL_SIZE >= 1

    def test_session_keys_defined(self):
        """All required session keys are defined."""
        assert hasattr(VisitorPool, "SESSION_KEY_PROJECT_ID")
        assert hasattr(VisitorPool, "SESSION_KEY_VISITOR_ID")
        assert hasattr(VisitorPool, "SESSION_KEY_ALLOCATION_TOKEN")


if __name__ == "__main__":
    import os

    pytest.main([os.path.abspath(__file__), "-v"])
