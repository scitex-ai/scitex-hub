#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for ``manage.py assert_visitor_pool_ready``.

The command exists because ``create_visitor_pool`` and
``reconcile_visitor_slots`` both exit 0 on a pool that can serve nobody —
the state production was measured in on 2026-08-16 (15 of 16 slots
quarantined) and the state CI landed in on PR #625. The value of a gate
is entirely in it going RED, so the red cases come first here.

Real DB via pytest-django ``TestCase``; no mocks (STX-NM001) — the rows
under test are the same ``VisitorAllocation`` rows allocation reads.
"""

import secrets
from datetime import timedelta

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.utils import timezone

from apps.infra.project_app.models import VisitorAllocation


def make_slot(number, *, quarantined=False, is_active=False, ready=True):
    """One allocation row in a named state (shared arrange step).

    ``expires_at`` and ``last_activity`` are set an hour out so an
    ``is_active`` row reads as a LIVE session rather than a stale one —
    ``get_pool_status`` treats a stale active row as reclaimable, which
    would quietly turn the "slot in use" case into something else.
    """
    now = timezone.now()
    return VisitorAllocation.objects.create(
        visitor_number=number,
        allocation_token=secrets.token_hex(16),
        expires_at=now + timedelta(hours=1),
        last_activity=now,
        quarantined=quarantined,
        is_active=is_active,
        workspace_ready=ready,
    )


class TestGateGoesRed(TestCase):
    """A pool that cannot hand out a writable slot must fail the job."""

    def test_no_allocation_rows_at_all_is_rejected(self):
        # Arrange — exactly what `create_visitor_pool` alone leaves behind:
        # users and projects exist, allocation rows do not.
        rejects = pytest.raises(CommandError)
        # Act
        VisitorAllocation.objects.all().delete()
        # Assert
        with rejects:
            call_command("assert_visitor_pool_ready")

    def test_all_slots_quarantined_is_rejected(self):
        # Arrange — the measured production state.
        for number in range(1, 5):
            make_slot(number, quarantined=True, ready=False)
        # Act
        rejects = pytest.raises(CommandError)
        # Assert
        with rejects:
            call_command("assert_visitor_pool_ready")

    def test_slot_awaiting_wipe_verify_is_not_counted_ready(self):
        # Arrange — released but never re-verified (Celery outage shape).
        make_slot(1, quarantined=False, ready=False)
        # Act
        rejects = pytest.raises(CommandError)
        # Assert
        with rejects:
            call_command("assert_visitor_pool_ready")

    def test_slot_in_use_is_not_counted_ready(self):
        # Arrange — a live visitor holds the only slot.
        make_slot(1, is_active=True, ready=True)
        # Act
        rejects = pytest.raises(CommandError)
        # Assert
        with rejects:
            call_command("assert_visitor_pool_ready")

    def test_one_ready_slot_does_not_satisfy_a_min_of_two(self):
        # Arrange
        make_slot(1)
        # Act
        rejects = pytest.raises(CommandError)
        # Assert
        with rejects:
            call_command("assert_visitor_pool_ready", "--min", "2")

    def test_a_min_below_one_is_refused_as_uncheckable(self):
        # Arrange — `--min 0` would make the gate incapable of failing,
        # which is the exact defect it was written to catch.
        make_slot(1)
        # Act
        rejects = pytest.raises(CommandError)
        # Assert
        with rejects:
            call_command("assert_visitor_pool_ready", "--min", "0")


class TestGateGoesGreen(TestCase):
    """...and must not fail a pool that genuinely can serve a visitor."""

    def test_one_ready_slot_passes(self):
        # Arrange
        make_slot(1)
        # Act
        result = call_command("assert_visitor_pool_ready")
        # Assert — call_command returns None when the command did not raise.
        assert result is None

    def test_two_ready_slots_satisfy_a_min_of_two(self):
        # Arrange
        make_slot(1)
        make_slot(2)
        # Act
        result = call_command("assert_visitor_pool_ready", "--min", "2")
        # Assert
        assert result is None

    def test_one_ready_slot_passes_even_when_others_are_quarantined(self):
        # Arrange — the pool is degraded but still serves a real visitor,
        # so the capture it gates is honest and must be allowed to run.
        make_slot(1)
        make_slot(2, quarantined=True, ready=False)
        make_slot(3, quarantined=True, ready=False)
        # Act
        result = call_command("assert_visitor_pool_ready")
        # Assert
        assert result is None


# EOF
