#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A quarantined slot must not be described as "being prepared".

Card hub-quarantined-visitor-slots-are-reported-as-being-prepared-20260905.

MEASURED 2026-09-05 on the dev preview: all four visitor slots were
quarantined (ready 0, quarantined 4, allocated 0) and the UI told the
operator:

    "Visitor slots are being prepared - you are browsing read-only.
     Retry in a few minutes for a writable slot."

Both halves are false for quarantine. A quarantined slot is released by
``manage.py reconcile_visitor_slots --repair-only`` and by nothing else,
so no amount of retrying produces a writable one. The slots sat that way
for 2h45m while the product invited him to keep waiting.

The conflation was DOCUMENTED, not accidental: session_role.py listed
"post-rebuild boot fail-safe, Celery outage, or quarantine" under one
reason code with one message, and only the first of those three
self-heals.

This is the SECOND iteration of this bug. ``no_ready_slot`` itself exists
because a popover claimed "pool is full" at 0/16 (2026-07-08 iPhone
report, see test_visitor_failloud.py). The lesson both times is the same:
a reason code covering cases with opposite recovery semantics will tell
someone to do the wrong thing.

These assertions are on PURE copy resolution - no database, no Django
test client - so they run anywhere, including containers with no
PostgreSQL. The allocation-path behaviour that CHOOSES the code needs a
real pool and is covered by the existing visitor-pool suite.

One assertion per test (STX-TQ007), AAA markers (STX-TQ002).
"""

from apps.infra.project_app.services.visitor_pool import (
    READONLY_REASON_NEEDS_OPERATOR,
    READONLY_REASON_NO_READY_SLOT,
    READONLY_REASON_POOL_FULL,
    READONLY_REASON_UNKNOWN,
    readonly_reason_detail,
    readonly_reason_for_capacity_cause,
)


def test_needs_operator_copy_does_not_tell_the_user_to_retry():
    # Arrange
    reason = READONLY_REASON_NEEDS_OPERATOR
    # Act
    detail = readonly_reason_detail(reason)
    # Assert - "retry" is the exact advice that cannot work for a
    # quarantined slot, which is released only by an operator command
    assert "Retry" not in detail


def test_needs_operator_copy_says_an_administrator_is_required():
    # Arrange
    reason = READONLY_REASON_NEEDS_OPERATOR
    # Act
    detail = readonly_reason_detail(reason)
    # Assert
    assert "administrator" in detail


def test_needs_operator_is_not_the_same_copy_as_no_ready_slot():
    # Arrange
    needs_operator = READONLY_REASON_NEEDS_OPERATOR
    # Act
    detail = readonly_reason_detail(needs_operator)
    # Assert - the whole defect was these two sharing one message
    assert detail != readonly_reason_detail(READONLY_REASON_NO_READY_SLOT)


def test_no_ready_slot_keeps_its_retry_advice():
    # Arrange - a genuinely resetting slot DOES clear itself in seconds,
    # so this copy is correct and must not become collateral damage
    reason = READONLY_REASON_NO_READY_SLOT
    # Act
    detail = readonly_reason_detail(reason)
    # Assert
    assert "Retry in a few minutes" in detail


def test_pool_full_copy_is_unchanged():
    # Arrange
    reason = READONLY_REASON_POOL_FULL
    # Act
    detail = readonly_reason_detail(reason)
    # Assert
    assert "All visitor slots are in use" in detail


def test_an_unrecognised_code_still_gets_the_generic_but_true_copy():
    # Arrange - the module's standing rule: never a wrong SPECIFIC claim
    # for a code we do not recognise
    reason = "some-code-added-after-this-test"
    # Act
    detail = readonly_reason_detail(reason)
    # Assert
    assert "No writable visitor slot is available" in detail


def test_unknown_reason_gets_the_generic_copy():
    # Arrange
    reason = READONLY_REASON_UNKNOWN
    # Act
    detail = readonly_reason_detail(reason)
    # Assert
    assert "No writable visitor slot is available" in detail


# ---------------------------------------------------------------------------
# The RULE itself, not just the copy. Extracted from the allocator branch so
# it can be exercised without a database - the branch it replaced could only
# be reached by driving a real pool into each capacity state.
# ---------------------------------------------------------------------------


def test_quarantined_capacity_needs_an_operator():
    # Arrange - the state the dev preview was in for 2h45m
    cause = "quarantined"
    # Act
    reason = readonly_reason_for_capacity_cause(cause)
    # Assert
    assert reason == READONLY_REASON_NEEDS_OPERATOR


def test_unprovisioned_capacity_needs_an_operator():
    # Arrange - missing rows are not something waiting fixes either
    cause = "unprovisioned"
    # Act
    reason = readonly_reason_for_capacity_cause(cause)
    # Assert
    assert reason == READONLY_REASON_NEEDS_OPERATOR


def test_resetting_capacity_is_still_the_self_healing_reason():
    # Arrange - a slot mid wipe+verify DOES clear itself
    cause = "resetting"
    # Act
    reason = readonly_reason_for_capacity_cause(cause)
    # Assert
    assert reason == READONLY_REASON_NO_READY_SLOT


def test_an_unknown_capacity_cause_does_not_claim_an_operator_is_needed():
    # Arrange - a cause added to pool_health later must not silently
    # inherit the strongest claim
    cause = "some-cause-added-after-this-test"
    # Act
    reason = readonly_reason_for_capacity_cause(cause)
    # Assert
    assert reason == READONLY_REASON_NO_READY_SLOT


def test_no_capacity_cause_at_all_is_handled():
    # Arrange
    cause = None
    # Act
    reason = readonly_reason_for_capacity_cause(cause)
    # Assert
    assert reason == READONLY_REASON_NO_READY_SLOT
