#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A pool whose slots are all HELD must go red, not just one that is quarantined.

WHAT #628 GOT RIGHT, AND WHERE IT STOPS
PR #628 taught ``/api/server-health/`` to ask about the visitor pool at all —
a real fix for the 2026-08-16 incident, where all 16 slots sat quarantined for
~1h35m and every signal stayed green. Its predicate is::

    ready == 0        -> error
    quarantined > 0   -> warning

That catches "everything QUARANTINED". It does not catch "everything HELD",
and held is the commoner shape.

THE MEASUREMENT THAT MOTIVATES THIS FILE (prod, 2026-08-16 15:55:08Z)
A real anonymous visitor entered scitex.ai via /landing/ -> "Enter as visitor"
-> /enter/ and the RENDERED page carried::

    data-session-role = "readonly_visitor"       <- the shared fallback account
    banner: "Read-Only Mode / of 16 visitor slots available"

Seconds later, from the prod DB::

    total=16  quarantined=0  workspace-clean=12  ALLOCATABLE=1
    every row's expires_at within ~2 minutes of now

Under #628 this reports HEALTHY. ``quarantined > 0`` is false. ``ready == 0``
is false. Nothing lied; the guard was narrower than the property it claims to
protect. The product path was down for that visitor and the dot stayed green.

WHAT THESE TESTS PIN
- ``allocatable``, not "the workspace is clean", decides the colour. A slot
  that is clean but HELD cannot be handed to the next visitor.
- zero capacity names ITS OWN cause and ITS OWN repair. Naming the wrong one
  is worse than naming none: ``reconcile_visitor_slots --repair-only``
  re-cleans only ``quarantined=True`` rows, so on a saturated pool it is a
  no-op that reads as "I ran the documented fix and nothing changed".
- the all-quarantined path still goes red naming ``--repair-only`` (#628 must
  not regress).
- a pool with real headroom stays GREEN. This matters as much as the red case:
  a guard that never passes is disabled within a week.

SCOPE. This change makes the failure VISIBLE. Making it STOP — the TTL,
heartbeat and reaper asymmetry that lets one non-JS client burn a slot per
request — is card hub-visitor-slots-expire-in-minutes-and-never-return-
20260816 and is deliberately untouched here.

No DB and no network: ``check_visitor_pool`` takes a kwarg-only
``pool_status_fn`` seam — a tiny REAL function returning a measured status
dict. Nothing is mocked; the ORM counting is covered in test_pool_manager.py.
"""

from apps.infra.public_app.views.status.api.health import (
    _build_issues_list,
    _determine_overall_health,
)
from apps.infra.public_app.views.status.visitor_pool_health import (
    classify_visitor_pool,
)
from apps.infra.public_app.views.status.visitor_pool_health import (
    check_visitor_pool,
)

# THE CASE THAT MATTERS: every slot HELD by a live session, none quarantined,
# and twelve workspaces sitting clean underneath. "Clean" is what a human (and
# the ad-hoc prod query) reads as "ready"; it is not what the allocator serves.
ALL_HELD_STATUS = {
    "total": 16,
    "allocated": 16,
    "free": 0,
    "expired": 0,
    "quarantined": 0,
    "ready": 12,
    "live": 16,
    "reclaimable": 0,
    "resetting": 0,
    "missing": 0,
}

# The 2026-08-16 15:55:08Z snapshot: 1 allocatable of 16, nothing quarantined.
# The state a real visitor met while the badge was green.
MEASURED_1555Z_STATUS = {
    "total": 16,
    "allocated": 11,
    "free": 5,
    "expired": 1,
    "quarantined": 0,
    "ready": 1,
    "allocatable": 1,
    "live": 11,
    "reclaimable": 1,
    "resetting": 3,
    "missing": 0,
}

# The 2026-08-16 14:49Z outage: the shape #628 was written for.
ALL_QUARANTINED_STATUS = {
    "total": 16,
    "allocated": 0,
    "free": 16,
    "expired": 0,
    "quarantined": 16,
    "ready": 0,
    "allocatable": 0,
    "live": 0,
    "reclaimable": 0,
    "resetting": 0,
    "missing": 0,
}

# Released slots awaiting the async wipe+verify. The pool is not broken; the
# worker is. A pool repair would send the operator to the wrong process.
ALL_RESETTING_STATUS = {
    "total": 16,
    "allocated": 0,
    "free": 16,
    "expired": 0,
    "quarantined": 0,
    "ready": 0,
    "allocatable": 0,
    "live": 0,
    "reclaimable": 0,
    "resetting": 16,
    "missing": 0,
}

# Pool size configured, no rows created. Nothing to repair, only to create.
UNPROVISIONED_STATUS = {
    "total": 16,
    "allocated": 0,
    "free": 16,
    "expired": 0,
    "quarantined": 0,
    "ready": 0,
    "allocatable": 0,
    "live": 0,
    "reclaimable": 0,
    "resetting": 0,
    "missing": 16,
}

# Healthy with real headroom, and three visitors legitimately working.
HEALTHY_HEADROOM_STATUS = {
    "total": 16,
    "allocated": 3,
    "free": 13,
    "expired": 0,
    "quarantined": 0,
    "ready": 13,
    "allocatable": 13,
    "live": 3,
    "reclaimable": 0,
    "resetting": 0,
    "missing": 0,
}

# The normal post-deploy transient: most slots mid-wipe, capacity remaining.
POST_DEPLOY_TRANSIENT_STATUS = {
    "total": 16,
    "allocated": 0,
    "free": 16,
    "expired": 0,
    "quarantined": 0,
    "ready": 13,
    "allocatable": 13,
    "live": 0,
    "reclaimable": 0,
    "resetting": 3,
    "missing": 0,
}


def _status_data_for(pool_status: dict) -> dict:
    """Run the real check with an injected status source (no DB)."""
    status_data = {"services": [], "ssh_services": [], "api_services": []}
    check_visitor_pool(status_data, pool_status_fn=lambda: pool_status)
    return status_data


class TestEverySlotHeldIsRed:
    """The case #628 cannot produce. Held is not available."""

    def test_all_slots_held_reports_error_status(self):
        # Arrange — 0 quarantined, 12 clean, all 16 held by live sessions
        status_data = _status_data_for(ALL_HELD_STATUS)
        # Act
        overall_status, _color = _determine_overall_health(status_data)
        # Assert
        assert overall_status == "error"

    def test_all_slots_held_paints_the_public_dot_red(self):
        # Arrange
        status_data = _status_data_for(ALL_HELD_STATUS)
        # Act
        _overall_status, color = _determine_overall_health(status_data)
        # Assert — the only signal a non-staff visitor can see
        assert color == "#ef4444"

    def test_all_slots_held_reports_zero_allocatable_not_twelve_clean(self):
        # Arrange — the measured fixture above
        # Act
        entry = classify_visitor_pool(ALL_HELD_STATUS)
        # Assert — the whole point: 12 clean workspaces, 0 servable slots
        assert entry["allocatable"] == 0

    def test_all_slots_held_cause_is_saturated(self):
        # Arrange — the measured fixture above
        # Act
        entry = classify_visitor_pool(ALL_HELD_STATUS)
        # Assert
        assert entry["cause"] == "saturated"

    def test_all_slots_held_names_capacity_not_the_reconcile(self):
        # Arrange — the measured fixture above
        # Act
        entry = classify_visitor_pool(ALL_HELD_STATUS)
        # Assert — the NEGATIVE assertion is the test. --repair-only re-cleans
        # only quarantined rows, so offering it here is a no-op that reads to
        # the operator as "I ran the fix and nothing changed".
        assert "--repair-only" not in entry["message"]

    def test_all_slots_held_names_the_capacity_knob(self):
        # Arrange — the measured fixture above
        # Act
        entry = classify_visitor_pool(ALL_HELD_STATUS)
        # Assert
        assert "SCITEX_HUB_VISITOR_POOL_SIZE" in entry["message"]

    def test_all_slots_held_still_reports_zero_quarantined(self):
        # Arrange — the measured fixture above
        # Act — naming one cause must not hide the other buckets
        entry = classify_visitor_pool(ALL_HELD_STATUS)
        # Assert
        assert "0 quarantined" in entry["message"]

    def test_all_slots_held_states_the_visitor_consequence(self):
        # Arrange — the measured fixture above
        # Act
        entry = classify_visitor_pool(ALL_HELD_STATUS)
        # Assert
        assert "readonly-visitor" in entry["message"]

    def test_all_slots_held_raises_a_visitor_pool_issue(self):
        # Arrange
        status_data = _status_data_for(ALL_HELD_STATUS)
        # Act
        issues = _build_issues_list(status_data)
        # Assert
        assert [issue["service"] for issue in issues] == ["Visitor Pool"]


class TestMeasuredProdSnapshotIsNotGreen:
    """1 of 16 allocatable is one arrival from the outage, not health."""

    def test_one_allocatable_of_sixteen_is_not_ok(self):
        # Arrange — the exact state a real visitor met at 15:55:08Z
        status_data = _status_data_for(MEASURED_1555Z_STATUS)
        # Act
        overall_status, _color = _determine_overall_health(status_data)
        # Assert
        assert overall_status == "warning"

    def test_one_allocatable_of_sixteen_raises_an_issue(self):
        # Arrange
        status_data = _status_data_for(MEASURED_1555Z_STATUS)
        # Act
        issues = _build_issues_list(status_data)
        # Assert
        assert issues != []

    def test_one_allocatable_message_explains_the_recovery_delay(self):
        # Arrange — the measured fixture above
        # Act
        entry = classify_visitor_pool(MEASURED_1555Z_STATUS)
        # Assert — why 1 is not "fine": the slot does not come straight back
        assert "does not return for tens of minutes" in entry["message"]


class TestQuarantinedPoolStillRedWithItsOwnRepair:
    """#628's case must not regress."""

    def test_all_quarantined_reports_error_status(self):
        # Arrange
        status_data = _status_data_for(ALL_QUARANTINED_STATUS)
        # Act
        overall_status, _color = _determine_overall_health(status_data)
        # Assert
        assert overall_status == "error"

    def test_all_quarantined_cause_is_quarantined(self):
        # Arrange — the measured fixture above
        # Act
        entry = classify_visitor_pool(ALL_QUARANTINED_STATUS)
        # Assert
        assert entry["cause"] == "quarantined"

    def test_all_quarantined_names_the_reconcile(self):
        # Arrange — the measured fixture above
        # Act
        entry = classify_visitor_pool(ALL_QUARANTINED_STATUS)
        # Assert
        assert "reconcile_visitor_slots" in entry["message"]

    def test_all_quarantined_names_the_safe_repair_flag(self):
        # Arrange — the measured fixture above
        # Act — plain reconcile quarantines healthy slots too
        entry = classify_visitor_pool(ALL_QUARANTINED_STATUS)
        # Assert
        assert "--repair-only" in entry["message"]


class TestEachCauseNamesItsOwnRepair:
    """A repair that does nothing is worse than no repair named."""

    def test_resetting_pool_cause_is_resetting(self):
        # Arrange — the measured fixture above
        # Act
        entry = classify_visitor_pool(ALL_RESETTING_STATUS)
        # Assert
        assert entry["cause"] == "resetting"

    def test_resetting_pool_points_at_the_wipe_worker(self):
        # Arrange — the measured fixture above
        # Act — the pool is not broken; the worker is
        entry = classify_visitor_pool(ALL_RESETTING_STATUS)
        # Assert
        assert "celery_worker_vis" in entry["message"]

    def test_resetting_pool_does_not_name_the_reconcile(self):
        # Arrange — the measured fixture above
        # Act
        entry = classify_visitor_pool(ALL_RESETTING_STATUS)
        # Assert
        assert "--repair-only" not in entry["message"]

    def test_unprovisioned_pool_cause_is_unprovisioned(self):
        # Arrange — the measured fixture above
        # Act
        entry = classify_visitor_pool(UNPROVISIONED_STATUS)
        # Assert
        assert entry["cause"] == "unprovisioned"

    def test_unprovisioned_pool_names_pool_creation(self):
        # Arrange — the measured fixture above
        # Act — there is nothing to repair, only something to create
        entry = classify_visitor_pool(UNPROVISIONED_STATUS)
        # Assert
        assert "create_visitor_pool" in entry["message"]

    def test_mixed_cause_reports_the_dominant_one(self):
        # Arrange — 1 quarantined, 15 held: the quarantine is real but it is
        # not why capacity is zero.
        mixed = dict(
            ALL_HELD_STATUS, quarantined=1, live=15, allocated=15, ready=0
        )
        # Act
        entry = classify_visitor_pool(mixed)
        # Assert
        assert entry["cause"] == "saturated"

    def test_mixed_cause_still_reports_the_smaller_fault(self):
        # Arrange
        mixed = dict(
            ALL_HELD_STATUS, quarantined=1, live=15, allocated=15, ready=0
        )
        # Act
        entry = classify_visitor_pool(mixed)
        # Assert — choosing a cause must not hide a second fault
        assert "1 quarantined" in entry["message"]


class TestHealthyPoolStaysGreen:
    """A guard that never passes gets disabled within a week."""

    def test_pool_with_headroom_reports_healthy(self):
        # Arrange — 13 of 16 allocatable, 3 visitors working
        status_data = _status_data_for(HEALTHY_HEADROOM_STATUS)
        # Act
        overall_status, _color = _determine_overall_health(status_data)
        # Assert
        assert overall_status == "healthy"

    def test_pool_with_headroom_raises_no_issue(self):
        # Arrange
        status_data = _status_data_for(HEALTHY_HEADROOM_STATUS)
        # Act
        issues = _build_issues_list(status_data)
        # Assert
        assert issues == []

    def test_slots_in_use_do_not_raise_an_alarm(self):
        # Arrange — the measured fixture above
        # Act — keyed on quarantined/allocatable, never on allocatable < total
        entry = classify_visitor_pool(HEALTHY_HEADROOM_STATUS)
        # Assert
        assert entry["is_healthy"] is True

    def test_post_deploy_wipe_transient_stays_green(self):
        # Arrange — 3 slots mid-wipe is the NORMAL post-deploy state. An alarm
        # that fires on every deploy is an alarm that gets muted.
        status_data = _status_data_for(POST_DEPLOY_TRANSIENT_STATUS)
        # Act
        overall_status, _color = _determine_overall_health(status_data)
        # Assert
        assert overall_status == "healthy"

    def test_two_allocatable_is_the_floor_that_still_passes(self):
        # Arrange — exactly at the threshold
        at_floor = dict(HEALTHY_HEADROOM_STATUS, allocatable=2, ready=2, live=14,
                        allocated=14)
        # Act
        entry = classify_visitor_pool(at_floor)
        # Assert
        assert entry["is_healthy"] is True


class TestPayloadRemainsBackwardCompatible:
    """Three live consumers read these keys; the #628 suite reads them too."""

    def test_ready_is_an_alias_of_allocatable(self):
        # Arrange — the measured fixture above
        # Act
        entry = classify_visitor_pool(MEASURED_1555Z_STATUS)
        # Assert — same predicate, two names, one number
        assert entry["ready"] == entry["allocatable"]

    def test_allocated_still_reports_live_sessions(self):
        # Arrange — the measured fixture above
        # Act
        entry = classify_visitor_pool(MEASURED_1555Z_STATUS)
        # Assert
        assert entry["allocated"] == 11

    def test_legacy_payload_without_partition_keys_still_classifies(self):
        # Arrange — the pre-#628 dict shape, which three call sites still pass
        legacy = {"total": 16, "allocated": 0, "free": 16, "expired": 0,
                  "quarantined": 0, "ready": 16}
        # Act
        entry = classify_visitor_pool(legacy)
        # Assert
        assert entry["is_healthy"] is True

    def test_legacy_outage_payload_still_goes_red(self):
        # Arrange
        legacy = {"total": 16, "allocated": 0, "free": 16, "expired": 0,
                  "quarantined": 16, "ready": 0}
        # Act
        entry = classify_visitor_pool(legacy)
        # Assert
        assert entry["status"] == "error"

    def test_buckets_sum_to_total(self):
        # Arrange — the measured fixture above
        # Act
        entry = classify_visitor_pool(MEASURED_1555Z_STATUS)
        # Assert — the invariant, asserted rather than hoped for
        accounted = (
            entry["allocatable"] + entry["live"] + entry["reclaimable"]
            + entry["resetting"] + entry["quarantined"] + entry["missing"]
        )
        assert accounted == entry["total"]

    def test_repair_hint_matches_the_single_source(self):
        # Arrange — the hint is spelled out in the view (lazy-import rule) and
        # defined once in pool_health; this pins them to the same string.
        from apps.infra.project_app.services.visitor_pool.pool_health import (
            CAUSE_QUARANTINED,
            REPAIR_BY_CAUSE,
        )
        from apps.infra.public_app.views.status.visitor_pool_health import (
            VISITOR_POOL_REPAIR_HINT,
        )
        # Act
        canonical = REPAIR_BY_CAUSE[CAUSE_QUARANTINED]
        # Assert
        assert VISITOR_POOL_REPAIR_HINT.endswith(canonical)

    def test_inconsistent_partition_is_flagged_not_classified(self):
        # Arrange — buckets that cannot be true of a 16-slot pool
        broken = dict(ALL_HELD_STATUS, allocatable=9, missing=0, live=16)
        # Act
        entry = classify_visitor_pool(broken)
        # Assert — say "these numbers disagree", do not classify confidently
        assert entry["cause"] == "inconsistent"


if __name__ == "__main__":
    import os

    import pytest

    pytest.main([os.path.abspath(__file__)])

# EOF
