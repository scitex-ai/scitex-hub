#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Queue-liveness beacon — the watchdog for wedged celery workers.

Field bug (prod, measured 2026-07-14 and 2026-07-17): the celery workers
intermittently stop dispatching — ``inspect reserved`` shows a full
prefetch window (time_start=None, worker_pid=None), ``inspect active``
is empty, children idle, control channel answers — while the container
healthcheck (a redis ping) stays green forever, so the visitor-slot
re-clean queue silently stops draining and the pool cannot self-heal.

These tests pin the safety net without a redis server and without mock
libraries (repo policy):

* the pure core ``write_liveness_stamp`` runs against a hand-rolled
  fake client (just the ``.set`` it exercises);
* ``check_queue_liveness.sh`` — the actual docker healthcheck — runs as
  a REAL subprocess, with a generated fake ``redis`` module placed
  first on ``PYTHONPATH`` so its canned ``get`` drives every branch
  (fresh / missing / stale / garbage);
* the beat wiring and the .py↔.sh key/broker contract are asserted
  against the real settings object and the real script source — a
  drifted prefix would make the healthcheck read a key nobody writes
  (= permanent false unhealthy).

AAA + one assertion each, per repo convention. No DB required.
"""

import os
import subprocess
import time
from pathlib import Path

import pytest
from django.conf import settings

from apps.infra.public_app.tasks import (
    LIVENESS_KEY_PREFIX,
    liveness_key,
    queue_liveness_beacon,
    write_liveness_stamp,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
HEALTHCHECK_SCRIPT = (
    REPO_ROOT / "deployment" / "docker" / "common" / "scripts"
    / "check_queue_liveness.sh"
)


class FakeRedisClient:
    """Hand-rolled fake: only the ``.set`` the pure core exercises."""

    def __init__(self):
        self.writes = {}

    def set(self, key, value):
        self.writes[key] = value


class UnreachableRedisClient:
    """Hand-rolled fake for a down broker: every write raises."""

    def set(self, key, value):
        raise ConnectionError("broker unreachable")


def _run_healthcheck(tmp_path, fake_get_body, argv):
    """Run the real check_queue_liveness.sh with a generated fake ``redis``
    module first on PYTHONPATH, so its canned ``get`` drives the branch
    under test. Returns the CompletedProcess."""
    fake_redis = tmp_path / "redis.py"
    fake_redis.write_text(
        '"""Generated fake redis module for check_queue_liveness.sh tests."""\n'
        "import time\n"
        "\n"
        "\n"
        "class Redis:\n"
        "    @classmethod\n"
        "    def from_url(cls, url, **kwargs):\n"
        "        return cls()\n"
        "\n"
        "    def get(self, key):\n"
        f"        {fake_get_body}\n"
    )
    env = dict(os.environ)
    env["PYTHONPATH"] = str(tmp_path) + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        ["bash", str(HEALTHCHECK_SCRIPT), *argv],
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )


class TestLivenessKey:
    """Key construction — the contract the healthcheck script reads."""

    def test_liveness_key_prefixes_queue_name(self):
        # Arrange
        queue_name = "celery"
        # Act
        key = liveness_key(queue_name)
        # Assert
        assert key == "scitex:liveness:celery"

    def test_liveness_key_for_vis_queue(self):
        # Arrange
        queue_name = "vis_queue"
        # Act
        key = liveness_key(queue_name)
        # Assert
        assert key == "scitex:liveness:vis_queue"

    def test_liveness_key_rejects_empty_name(self):
        # Arrange
        queue_name = ""
        # Act
        # (the raising call below is the act; pytest.raises is the assertion)
        # Assert
        with pytest.raises(ValueError):
            liveness_key(queue_name)

    def test_liveness_key_rejects_whitespace_name(self):
        # Arrange
        queue_name = "   "
        # Act
        # (the raising call below is the act; pytest.raises is the assertion)
        # Assert
        with pytest.raises(ValueError):
            liveness_key(queue_name)


class TestWriteLivenessStamp:
    """Pure core of the beacon, driven through an injected fake client."""

    def test_stamp_lands_on_the_queue_key(self):
        # Arrange
        client = FakeRedisClient()
        # Act
        write_liveness_stamp(client, "celery", 1752700000.0)
        # Assert
        assert "scitex:liveness:celery" in client.writes

    def test_stamp_value_is_the_given_timestamp(self):
        # Arrange
        client = FakeRedisClient()
        # Act
        write_liveness_stamp(client, "vis_queue", 1752700000.0)
        # Assert
        assert client.writes["scitex:liveness:vis_queue"] == 1752700000.0

    def test_returns_the_written_key(self):
        # Arrange
        client = FakeRedisClient()
        # Act
        key = write_liveness_stamp(client, "vis_queue", 1752700000.0)
        # Assert
        assert key == "scitex:liveness:vis_queue"

    def test_propagates_broker_errors(self):
        # Arrange — redis down IS unhealthy; the beacon must fail loud,
        # never swallow (no silent fallback).
        client = UnreachableRedisClient()
        # Act
        # (the raising call below is the act; pytest.raises is the assertion)
        # Assert
        with pytest.raises(ConnectionError):
            write_liveness_stamp(client, "celery", time.time())

    def test_rejects_blank_queue_name(self):
        # Arrange — a stamp vouching for no queue must never be written.
        client = FakeRedisClient()
        # Act
        # (the raising call below is the act; pytest.raises is the assertion)
        # Assert
        with pytest.raises(ValueError):
            write_liveness_stamp(client, "", time.time())

    def test_blank_queue_name_writes_nothing(self):
        # Arrange — the ValueError itself is pinned by the sibling test
        # above; this one pins that the refusal happens BEFORE any write.
        client = FakeRedisClient()
        # Act
        try:
            write_liveness_stamp(client, "", time.time())
        except ValueError:
            pass
        # Assert
        assert client.writes == {}


class TestQueueLivenessBeaconTask:
    """The celery task shell around the pure core."""

    def test_beacon_task_name_is_stable(self):
        # Arrange — the beat entries reference this exact string; a rename
        # silently unregisters the watchdog.
        expected = "apps.infra.public_app.tasks.queue_liveness_beacon"
        # Act
        registered = queue_liveness_beacon.name
        # Assert
        assert registered == expected


class TestBeatScheduleWiring:
    """CELERY_BEAT_SCHEDULE seeds the two PeriodicTask rows —
    django_celery_beat's DatabaseScheduler upserts these by name at every
    beat boot, including options.queue → PeriodicTask.queue."""

    def test_beat_schedules_beacon_onto_default_queue(self):
        # Arrange
        entry = settings.CELERY_BEAT_SCHEDULE["queue-liveness-beacon-celery"]
        # Act
        routed_queue = entry["options"]["queue"]
        # Assert
        assert routed_queue == "celery"

    def test_beat_schedules_beacon_onto_vis_queue(self):
        # Arrange
        entry = settings.CELERY_BEAT_SCHEDULE["queue-liveness-beacon-vis-queue"]
        # Act
        routed_queue = entry["options"]["queue"]
        # Assert
        assert routed_queue == "vis_queue"

    def test_beat_beacon_arg_names_the_routed_default_queue(self):
        # Arrange — the stamp must vouch for the queue that carried it.
        entry = settings.CELERY_BEAT_SCHEDULE["queue-liveness-beacon-celery"]
        # Act
        beacon_args = entry["args"]
        # Assert
        assert list(beacon_args) == [entry["options"]["queue"]]

    def test_beat_beacon_arg_names_the_routed_vis_queue(self):
        # Arrange
        entry = settings.CELERY_BEAT_SCHEDULE["queue-liveness-beacon-vis-queue"]
        # Act
        beacon_args = entry["args"]
        # Assert
        assert list(beacon_args) == [entry["options"]["queue"]]

    def test_beat_beacon_fires_every_120_seconds(self):
        # Arrange
        entry = settings.CELERY_BEAT_SCHEDULE["queue-liveness-beacon-celery"]
        # Act
        interval = entry["schedule"]
        # Assert
        assert interval == 120.0

    def test_beat_beacon_has_no_expiry(self):
        # Arrange — expiring beacons on a merely-slow queue would silently
        # shrink the healthcheck's 600s budget to the 120s interval; a LATE
        # beacon still proves dispatch, so it must never expire.
        entry = settings.CELERY_BEAT_SCHEDULE["queue-liveness-beacon-celery"]
        # Act
        options = entry["options"]
        # Assert
        assert "expires" not in options

    def test_beat_beacon_entries_reference_registered_task(self):
        # Arrange
        entry = settings.CELERY_BEAT_SCHEDULE["queue-liveness-beacon-celery"]
        # Act
        scheduled_task_name = entry["task"]
        # Assert
        assert scheduled_task_name == queue_liveness_beacon.name


class TestHealthcheckScriptContract:
    """The .sh reader and the .py writer must share one contract — a
    drifted key prefix or broker resolution reads a key nobody writes."""

    def test_healthcheck_script_shares_key_prefix(self):
        # Arrange
        script_source = HEALTHCHECK_SCRIPT.read_text()
        # Act
        prefix_present = LIVENESS_KEY_PREFIX in script_source
        # Assert
        assert prefix_present

    def test_healthcheck_script_reads_broker_env_var(self):
        # Arrange
        script_source = HEALTHCHECK_SCRIPT.read_text()
        # Act
        env_var_present = "SCITEX_HUB_CELERY_BROKER_URL" in script_source
        # Assert
        assert env_var_present

    def test_healthcheck_script_defaults_to_broker_db(self):
        # Arrange — must match CELERY_BROKER_URL's default in
        # config/settings/settings_celery.py (broker DB 1, not cache DB).
        script_source = HEALTHCHECK_SCRIPT.read_text()
        # Act
        default_present = "redis://redis:6379/1" in script_source
        # Assert
        assert default_present


class TestHealthcheckScriptBehavior:
    """Run the REAL script; a generated fake redis module (first on
    PYTHONPATH) cans each broker state. Missing/stale/garbage must all
    fail loud — a wedge must never read as healthy."""

    def test_fresh_stamp_is_healthy(self, tmp_path):
        # Arrange
        fake_get = "return str(time.time() - 30).encode()"
        # Act
        result = _run_healthcheck(tmp_path, fake_get, ["celery", "600"])
        # Assert
        assert result.returncode == 0

    def test_missing_stamp_is_unhealthy(self, tmp_path):
        # Arrange — MISSING key = unhealthy by design (no silent fallback).
        fake_get = "return None"
        # Act
        result = _run_healthcheck(tmp_path, fake_get, ["celery", "600"])
        # Assert
        assert result.returncode == 1

    def test_missing_stamp_message_names_the_queue(self, tmp_path):
        # Arrange
        fake_get = "return None"
        # Act
        result = _run_healthcheck(tmp_path, fake_get, ["vis_queue", "600"])
        # Assert
        assert "vis_queue" in result.stderr

    def test_stale_stamp_is_unhealthy(self, tmp_path):
        # Arrange — stamp far older than the 600s budget.
        fake_get = "return str(time.time() - 99999).encode()"
        # Act
        result = _run_healthcheck(tmp_path, fake_get, ["celery", "600"])
        # Assert
        assert result.returncode == 1

    def test_stale_stamp_message_reports_age_and_budget(self, tmp_path):
        # Arrange — "<age>s ago (budget 600s)" is the loud diagnosis line;
        # the exact age digits round nondeterministically, the phrase does
        # not.
        fake_get = "return str(time.time() - 99999).encode()"
        # Act
        result = _run_healthcheck(tmp_path, fake_get, ["celery", "600"])
        # Assert
        assert "ago (budget 600s)" in result.stderr

    def test_garbage_stamp_is_unhealthy(self, tmp_path):
        # Arrange — a corrupt stamp must never read as healthy.
        fake_get = 'return b"not-a-timestamp"'
        # Act
        result = _run_healthcheck(tmp_path, fake_get, ["celery", "600"])
        # Assert
        assert result.returncode == 1

    def test_max_age_defaults_to_600_seconds(self, tmp_path):
        # Arrange — 700s-old stamp, no explicit budget argument.
        fake_get = "return str(time.time() - 700).encode()"
        # Act
        result = _run_healthcheck(tmp_path, fake_get, ["celery"])
        # Assert
        assert result.returncode == 1

    def test_missing_queue_argument_is_a_usage_error(self, tmp_path):
        # Arrange
        fake_get = "return None"
        # Act
        result = _run_healthcheck(tmp_path, fake_get, [])
        # Assert
        assert result.returncode == 2


if __name__ == "__main__":
    pytest.main([os.path.abspath(__file__)])

# EOF
