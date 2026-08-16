#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Beat-schedule expiry — the gate against immortal periodic messages.

Field bug (prod, measured 2026-07-21): every ``CELERY_BEAT_SCHEDULE``
entry declared its expiry as ``options={"expires": ...}`` — celery's
producer-side keyword. But beat runs django_celery_beat's
DatabaseScheduler, whose ``ModelEntry._unpack_options()`` maps ONLY
``expire_seconds`` onto the seeded PeriodicTask row; ``expires`` fell
into ``**kwargs`` and was SILENTLY DISCARDED. Every periodic message
shipped immortal, so whenever drain rate < production rate the default
queue grew without bound — 50,199 messages (~6,000 copies of each
minute-ly task ≈ 4 days) on prod, which starved the queue-liveness
beacon, tripped the container healthcheck, and put autoheal into a
restart loop.

These tests run each schedule entry's options through the REAL
``ModelEntry._unpack_options`` so a future typo (``expires``) or a
django_celery_beat signature change fails loudly instead of silently
re-shipping immortal messages.

django_celery_beat is a HARD import here, never a skip: it is the
scheduler prod actually runs (``CELERY_BEAT_SCHEDULER``), and a skipped
gate would be green while checking nothing — a gate that cannot fail is
not a gate.

AAA + one assertion each, per repo convention. No DB required
(``_unpack_options`` is a pure classmethod).
"""

import os
import re
from pathlib import Path

import pytest
from django.conf import settings

try:
    from django_celery_beat.schedulers import ModelEntry
except ImportError as exc:  # no skip: an uncheckable gate must fail loudly
    raise ImportError(
        "django_celery_beat must be importable for this gate: it is the "
        "scheduler prod runs (CELERY_BEAT_SCHEDULER) and this test exists to "
        "prove its ModelEntry._unpack_options maps our expiry options onto "
        "the PeriodicTask row. Skipping would green-light immortal beat "
        "messages (2026-07-21 50k-backlog incident)."
    ) from exc

REPO_ROOT = Path(__file__).resolve().parents[3]
SETTINGS_CELERY_PATH = REPO_ROOT / "config" / "settings" / "settings_celery.py"
SETTINGS_DEV_PATH = REPO_ROOT / "config" / "settings" / "settings_dev.py"

# The ONLY entries allowed to ship without expiry, by design: a LATE beacon
# still proves the worker dispatches, whereas an expiring beacon on a
# merely-slow queue would silently shrink the healthcheck's 600s budget to
# the 120s beat interval (see settings_celery.py). Any NEW entry that wants
# immortality must be consciously added here with a reason.
NO_EXPIRY_BY_DESIGN = frozenset(
    {
        "queue-liveness-beacon-celery",
        "queue-liveness-beacon-vis-queue",
    }
)

# The active (test-env = settings_dev) schedule is base settings_celery
# entries plus the dev overrides — every declared entry is visible here.
_EXPIRING_ENTRY_NAMES = sorted(
    name
    for name in settings.CELERY_BEAT_SCHEDULE
    if name not in NO_EXPIRY_BY_DESIGN
)

# A dict-literal "expires" KEY at line start (comments start with '#', so
# prose mentions of the word never match).
_EXPIRES_KEY_PATTERN = re.compile(r'^\s*"expires"\s*:', re.MULTILINE)


class TestScheduleDeclaresExpireSeconds:
    """Every non-beacon entry must carry the key DatabaseScheduler reads."""

    @pytest.mark.parametrize("entry_name", _EXPIRING_ENTRY_NAMES)
    def test_entry_declares_expire_seconds(self, entry_name):
        # Arrange
        entry = settings.CELERY_BEAT_SCHEDULE[entry_name]
        # Act
        options = entry.get("options", {})
        # Assert
        assert "expire_seconds" in options

    @pytest.mark.parametrize("entry_name", _EXPIRING_ENTRY_NAMES)
    def test_entry_never_uses_producer_side_expires(self, entry_name):
        # Arrange — the exact typo that shipped the 50k backlog.
        entry = settings.CELERY_BEAT_SCHEDULE[entry_name]
        # Act
        options = entry.get("options", {})
        # Assert
        assert "expires" not in options

    @pytest.mark.parametrize("entry_name", _EXPIRING_ENTRY_NAMES)
    def test_expiry_budget_is_shorter_than_the_interval(self, entry_name):
        # Arrange — a stale run must die before the next one fires, or the
        # queue still grows whenever drain rate < production rate.
        entry = settings.CELERY_BEAT_SCHEDULE[entry_name]
        # Act
        budget = entry["options"]["expire_seconds"]
        # Assert
        assert budget < entry["schedule"]


class TestUnpackOptionsCarriesExpiry:
    """Round-trip through the REAL scheduler mapping — fails on a typo in
    our options AND on a django_celery_beat signature change."""

    @pytest.mark.parametrize("entry_name", _EXPIRING_ENTRY_NAMES)
    def test_unpacked_row_carries_non_null_expire_seconds(self, entry_name):
        # Arrange
        entry = settings.CELERY_BEAT_SCHEDULE[entry_name]
        # Act
        row_fields = ModelEntry._unpack_options(**entry["options"])
        # Assert
        assert row_fields["expire_seconds"] is not None

    def test_producer_side_expires_is_dropped_by_the_scheduler(self):
        # Arrange — pin the failure MODE itself: DatabaseScheduler discards
        # celery's producer-side keyword. If a future django_celery_beat
        # starts honoring it, this fails and the comments in
        # settings_celery.py need a rewrite.
        options_with_typo = {"expires": 55.0}
        # Act
        row_fields = ModelEntry._unpack_options(**options_with_typo)
        # Assert
        assert row_fields["expire_seconds"] is None


class TestBeaconsStayImmortal:
    """The two liveness beacons must declare NO expiry, in any spelling —
    expiring them would shrink the healthcheck's 600s budget to 120s."""

    @pytest.mark.parametrize("entry_name", sorted(NO_EXPIRY_BY_DESIGN))
    def test_beacon_declares_no_expiry(self, entry_name):
        # Arrange — KeyError here means the beacon entry itself vanished,
        # which is its own loud failure.
        entry = settings.CELERY_BEAT_SCHEDULE[entry_name]
        # Act
        options = entry.get("options", {})
        # Assert
        assert not ({"expires", "expire_seconds"} & set(options))


class TestSettingsSourceNeverSpellsExpires:
    """The active-schedule tests above cannot see a base entry that
    settings_dev overrides (the override wins in-process), so also gate
    the SOURCE files: no dict-literal "expires" key may reappear."""

    def test_settings_celery_source_has_no_expires_key(self):
        # Arrange
        source = SETTINGS_CELERY_PATH.read_text()
        # Act
        matches = _EXPIRES_KEY_PATTERN.findall(source)
        # Assert
        assert matches == []

    def test_settings_dev_source_has_no_expires_key(self):
        # Arrange
        source = SETTINGS_DEV_PATH.read_text()
        # Act
        matches = _EXPIRES_KEY_PATTERN.findall(source)
        # Assert
        assert matches == []

    def test_collect_server_metrics_is_owned_by_base_settings(self):
        # Arrange — prod's minute-ly metrics collection must be seeded by
        # settings_celery.py, not depend on an unmanaged PeriodicTask DB row
        # (the SSoT violation the 2026-07-21 incident surfaced).
        source = SETTINGS_CELERY_PATH.read_text()
        # Act
        entry_declared = '"collect-server-metrics"' in source
        # Assert
        assert entry_declared


if __name__ == "__main__":
    pytest.main([os.path.abspath(__file__)])

# EOF
