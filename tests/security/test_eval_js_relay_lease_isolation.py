#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Relay-group isolation keyed on the LEASE, not the username.

WHY THIS FILE REPLACES THE USERNAME-BASED VERSION.

`test_eval_js_relay_group_isolation.py` asserts that two sockets sharing a
username must not receive each other's frames. That property is WRONG, and a
correct fix must not satisfy it: one human with two browser tabs is two sockets
on one username, and both SHOULD receive the frame. Satisfying that test would
mean breaking multi-tab delivery.

The property actually required is about the LEASE:

    two sockets, DIFFERENT leases of one seat   ->  MUST NOT share a group
    two sockets, SAME lease (one human, tabs)   ->  MUST share a group
    a user with NO lease (regular / onsite MCP) ->  group unchanged from today

The third line is the constraint that killed the obvious "key it on the
session" fix: the onsite MCP producer authenticates via an HMAC header and has
no Django session, so anything session-derived silently addresses a group no
consumer has joined — and `group_send` to an empty group is not an error.

`VisitorAllocation.allocation_token` (project_app/models/core.py:58) is the
per-lease value that makes all three lines true at once. It changes when a seat
is re-leased, is identical for two tabs of one lease, and does not exist for
non-visitor users.

STATUS: these tests describe the INTENDED behaviour and FAIL against the
current implementation. They are the gate the fix has to turn.
Card: hub-eval-js-relay-visitor-seat-recycling-20260805.
"""

import pytest

pytestmark = pytest.mark.asyncio

SEAT = "visitor-007"
LEASE_A = "tok-aaaaaaaaaaaaaaaa"
LEASE_B = "tok-bbbbbbbbbbbbbbbb"


class _StubUser:
    """The two attributes the consumer reads, plus the lease under test."""

    def __init__(self, username, allocation_token=None):
        self.username = username
        self.is_authenticated = True
        self.allocation_token = allocation_token


def _group(user):
    """The group name under test.

    Imported lazily so this file fails with a clear ImportError, rather than a
    collection error, while the helper does not exist yet.
    """
    from apps.infra.llm_app.relay_groups import relay_group_for

    return relay_group_for(user)


async def test_different_leases_of_one_seat_get_different_groups():
    """The leak: a re-leased seat must not address the previous occupant."""
    # Arrange
    previous_occupant = _StubUser(SEAT, LEASE_A)
    later_occupant = _StubUser(SEAT, LEASE_B)

    # Act
    same_group = _group(previous_occupant) == _group(later_occupant)

    # Assert
    assert same_group is False, (
        "CROSS-USER LEAK: two DIFFERENT leases of seat "
        f"{SEAT!r} resolve to the same relay group, so a frame sent by the "
        "current occupant reaches the previous occupant's still-open socket "
        "and executes via new Function() at eval-js-relay.ts:24."
    )


async def test_two_tabs_of_one_lease_share_a_group():
    """The feature: one human's second tab must still receive frames.

    This is the test a username-based 'fix' would fail. It exists so that
    closing the leak cannot silently break multi-tab delivery.
    """
    # Arrange
    tab_one = _StubUser(SEAT, LEASE_A)
    tab_two = _StubUser(SEAT, LEASE_A)

    # Act
    same_group = _group(tab_one) == _group(tab_two)

    # Assert
    assert same_group is True, (
        "REGRESSION: two tabs of the SAME lease resolve to different relay "
        "groups, so a user's own second tab would stop receiving eval-js "
        "frames. Closing the leak must not cost multi-tab delivery."
    )


async def test_a_user_with_no_lease_keeps_todays_group_name():
    """The onsite MCP producer has no lease and must be unaffected.

    It authenticates by HMAC header with no Django session and no
    VisitorAllocation row. If its group name changes, `group_send` addresses a
    group nobody joined — which is NOT an error, so the feature would fail
    silently.
    """
    # Arrange
    regular_user = _StubUser("ywatanabe", allocation_token=None)

    # Act
    group = _group(regular_user)

    # Assert
    assert group == "eval_js_ywatanabe", (
        "The group name for a user with no lease changed. The onsite MCP "
        "producer would then group_send to a group no consumer has joined, "
        "and that failure is SILENT."
    )


async def test_two_seats_never_collide():
    """Sanity: distinct seats stay distinct regardless of lease handling."""
    # Arrange
    seat_a = _StubUser("visitor-007", LEASE_A)
    seat_b = _StubUser("visitor-008", LEASE_A)

    # Act
    same_group = _group(seat_a) == _group(seat_b)

    # Assert
    assert same_group is False, (
        "Two DIFFERENT seats resolved to the same relay group — the lease "
        "suffix has swallowed the identity it was meant to qualify."
    )


if __name__ == "__main__":
    import os

    pytest.main([os.path.abspath(__file__)])
