"""The spend-control behaviour matrix, enumerated (pure, no database).

Every (standing x cap level x action) cell is asserted, so the table in
``apps/infra/spend_app/services/policy.py`` cannot drift from the code.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from apps.infra.spend_app.services.policy import (
    Action,
    CapLevel,
    Run,
    Standing,
    cap_level,
    clamp_cap,
    decide,
    percent_used,
    running_verdict,
)

NOW = datetime(2026, 11, 27, 12, 0, tzinfo=timezone.utc)
GRACE = timedelta(minutes=15)

NEW_WORK = (Action.START_COMPUTE, Action.SUBMIT_JOB, Action.WRITE_STORAGE)
ALWAYS_ALLOWED = (Action.READ, Action.DELETE_STORAGE, Action.CHANGE_CAP, Action.PAY)


@pytest.mark.parametrize(
    "spend,cap,level",
    [
        ("0", "10", CapLevel.UNDER),
        ("4.99", "10", CapLevel.UNDER),
        ("5", "10", CapLevel.HALF),
        ("7.99", "10", CapLevel.HALF),
        ("8", "10", CapLevel.WARN),
        ("9.99", "10", CapLevel.WARN),
        ("10", "10", CapLevel.REACHED),
        ("25", "10", CapLevel.REACHED),
        ("0", "0", CapLevel.UNDER),
        ("0.0001", "0", CapLevel.REACHED),
    ],
)
def test_cap_level_maps_spend_to_the_highest_crossed_threshold(spend, cap, level):
    # Arrange
    spend, cap = Decimal(spend), Decimal(cap)
    # Act
    result = cap_level(spend, cap)
    # Assert
    assert result is level


@pytest.mark.parametrize(
    "spend,cap,expected", [("8", "10", 80), ("0", "0", 0), ("1", "0", 100)]
)
def test_percent_used_rounds_and_treats_a_zero_cap_as_all_or_nothing(
    spend, cap, expected
):
    # Arrange
    spend, cap = Decimal(spend), Decimal(cap)
    # Act
    result = percent_used(spend, cap)
    # Assert
    assert result == expected


@pytest.mark.parametrize("action", ALWAYS_ALLOWED)
@pytest.mark.parametrize("standing", list(Standing))
@pytest.mark.parametrize("level", list(CapLevel))
def test_reading_deleting_paying_and_changing_the_cap_are_never_refused(
    action, standing, level
):
    # Arrange
    cell = (standing, level, action)
    # Act
    decision = decide(*cell)
    # Assert
    assert decision.allowed


@pytest.mark.parametrize("action", NEW_WORK)
@pytest.mark.parametrize("level", [CapLevel.UNDER, CapLevel.HALF, CapLevel.WARN])
def test_good_standing_under_the_cap_allows_new_work(action, level):
    # Arrange
    standing = Standing.GOOD
    # Act
    decision = decide(standing, level, action)
    # Assert
    assert decision.allowed


@pytest.mark.parametrize(
    "action,code",
    [
        (Action.START_COMPUTE, "spend_cap_reached"),
        (Action.SUBMIT_JOB, "spend_cap_reached"),
        (Action.WRITE_STORAGE, "storage_read_only"),
    ],
)
def test_at_the_cap_new_work_is_refused_and_storage_is_read_only(action, code):
    # Arrange
    standing, level = Standing.GOOD, CapLevel.REACHED
    # Act
    decision = decide(standing, level, action)
    # Assert
    assert (decision.allowed, decision.code) == (False, code)


@pytest.mark.parametrize("action", NEW_WORK)
@pytest.mark.parametrize("level", list(CapLevel))
def test_past_due_in_payment_grace_keeps_working(action, level):
    # Arrange
    standing = Standing.PAST_DUE
    # Act
    decision = decide(standing, level, action)
    # Assert
    assert decision.allowed


@pytest.mark.parametrize("action", NEW_WORK)
@pytest.mark.parametrize("level", list(CapLevel))
def test_restricted_account_refuses_all_new_work(action, level):
    # Arrange
    standing = Standing.RESTRICTED
    # Act
    decision = decide(standing, level, action)
    # Assert
    assert (decision.allowed, decision.code) == (False, "account_restricted")


def test_shadow_mode_never_refuses_but_records_the_refusal_it_would_make():
    # Arrange
    cell = (Standing.GOOD, CapLevel.REACHED, Action.START_COMPUTE)
    # Act
    decision = decide(*cell, mode="shadow")
    # Assert
    assert (decision.allowed, decision.shadowed, decision.code) == (
        True,
        True,
        "spend_cap_reached",
    )


def test_running_work_under_the_cap_keeps_running():
    # Arrange
    standing, level = Standing.GOOD, CapLevel.WARN
    # Act
    verdict = running_verdict(standing, level, reached_at=None, now=NOW, grace=GRACE)
    # Assert
    assert verdict.verdict is Run.RUN


def test_running_work_at_the_cap_is_warned_with_the_stop_time_during_grace():
    # Arrange
    reached = NOW - timedelta(minutes=5)
    # Act
    verdict = running_verdict(
        Standing.GOOD, CapLevel.REACHED, reached_at=reached, now=NOW, grace=GRACE
    )
    # Assert
    assert (verdict.verdict, verdict.stop_at) == (Run.WARN, reached + GRACE)


def test_running_work_at_the_cap_is_stopped_when_the_grace_window_ends():
    # Arrange
    reached = NOW - GRACE
    # Act
    verdict = running_verdict(
        Standing.GOOD, CapLevel.REACHED, reached_at=reached, now=NOW, grace=GRACE
    )
    # Assert
    assert (verdict.verdict, verdict.reason) == (Run.STOP, "spend_cap_reached")


def test_running_work_on_a_restricted_account_is_stopped():
    # Arrange
    standing = Standing.RESTRICTED
    # Act
    verdict = running_verdict(
        standing, CapLevel.UNDER, reached_at=None, now=NOW, grace=GRACE
    )
    # Assert
    assert (verdict.verdict, verdict.reason) == (Run.STOP, "account_restricted")


def test_running_work_in_payment_grace_keeps_running_even_at_the_cap():
    # Arrange
    standing = Standing.PAST_DUE
    # Act
    verdict = running_verdict(
        standing, CapLevel.REACHED, reached_at=NOW, now=NOW, grace=GRACE
    )
    # Assert
    assert verdict.verdict is Run.RUN


def test_shadow_mode_downgrades_a_running_work_stop_to_a_warning():
    # Arrange
    standing = Standing.RESTRICTED
    # Act
    verdict = running_verdict(
        standing, CapLevel.UNDER, reached_at=None, now=NOW, grace=GRACE, mode="shadow"
    )
    # Assert
    assert verdict.verdict is Run.WARN


def test_clamp_cap_rounds_a_valid_cap_to_cents():
    # Arrange
    requested = Decimal("12.345")
    # Act
    cap = clamp_cap(requested, max_cap=Decimal("200"))
    # Assert
    assert cap == Decimal("12.35")


@pytest.mark.parametrize("requested", ["-1", "200.01"])
def test_clamp_cap_refuses_a_cap_outside_zero_to_the_plan_maximum(requested):
    # Arrange
    value = Decimal(requested)
    # Act
    call = lambda: clamp_cap(value, max_cap=Decimal("200"))  # noqa: E731
    # Assert
    with pytest.raises(ValueError):
        call()
