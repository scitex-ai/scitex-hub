"""Contract tests for the long-lived-checkout source-dirt tripwire."""
from __future__ import annotations

import io
import json
import subprocess
from pathlib import Path

from scitex_hub._jobs import (
    SOURCE_DIRT_CADENCE,
    SOURCE_DIRT_CHECKOUTS,
    SOURCE_DIRT_TIMEOUT_SEC,
    provide_jobs,
    provide_placement,
)
from scitex_hub._jobs.source_dirt_tripwire import (
    DELIVERY_FAILED,
    DELIVERY_NOT_REQUIRED,
    DELIVERY_UNCONFIRMED,
    emit_event,
    run,
)


def _tripwire_jobs():
    return [job for job in provide_jobs() if "source-dirt" in job.name]


def test_every_declared_long_lived_checkout_has_one_stable_timer():
    jobs = _tripwire_jobs()
    assert len(jobs) == len(SOURCE_DIRT_CHECKOUTS) > 0
    assert {job.name for job in jobs} == {
        f"scitex-hub-source-dirt-{label}" for label, _, _ in SOURCE_DIRT_CHECKOUTS
    }
    assert all(job.kind == "timer" and job.on_unit_active_sec == SOURCE_DIRT_CADENCE for job in jobs)


def test_each_job_is_self_bounded_and_names_its_checkout_explicitly():
    by_name = {job.name: job for job in _tripwire_jobs()}
    for label, _, checkout in SOURCE_DIRT_CHECKOUTS:
        job = by_name[f"scitex-hub-source-dirt-{label}"]
        assert job.timeout_sec == SOURCE_DIRT_TIMEOUT_SEC
        assert job.command.startswith(f"/usr/bin/timeout {SOURCE_DIRT_TIMEOUT_SEC} ")
        assert job.command.endswith(f" --checkout {checkout}")


def test_each_job_is_placed_only_on_the_host_that_holds_its_checkout():
    placements = {row.job: row.hosts for row in provide_placement()}
    for label, host, _ in SOURCE_DIRT_CHECKOUTS:
        assert placements[f"scitex-hub-source-dirt-{label}"] == (host,)


def test_runner_uses_explicit_cwd_and_suppresses_child_output(tmp_path, monkeypatch):
    secret = "PASSWORD=must-never-escape"
    seen = {}
    def fake_run(argv, **kwargs):
        seen.update(argv=argv, kwargs=kwargs)
        return subprocess.CompletedProcess(argv, 7, secret, secret)
    monkeypatch.setattr(subprocess, "run", fake_run)
    stream = io.StringIO()
    assert run(tmp_path, writer=stream.write) == 7
    assert seen["kwargs"]["cwd"] == tmp_path
    assert seen["kwargs"]["timeout"] < SOURCE_DIRT_TIMEOUT_SEC
    assert secret not in stream.getvalue()
    event = json.loads(stream.getvalue())
    assert event["check_exit_code"] == 7 and event["delivery"] == DELIVERY_UNCONFIRMED


def test_healthy_run_needs_no_alert_delivery(tmp_path, monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(a, 0, "", ""))
    stream = io.StringIO()
    assert run(tmp_path, writer=stream.write) == 0
    assert json.loads(stream.getvalue())["delivery"] == DELIVERY_NOT_REQUIRED


def test_timeout_is_nonzero_and_reported_without_output(tmp_path, monkeypatch):
    def timed_out(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], kwargs["timeout"], output="credential", stderr="secret")
    monkeypatch.setattr(subprocess, "run", timed_out)
    stream = io.StringIO()
    assert run(tmp_path, writer=stream.write) == 124
    assert "credential" not in stream.getvalue() and "secret" not in stream.getvalue()


def test_failed_event_emission_is_third_delivery_state_and_fails_loudly():
    def broken(_text):
        raise OSError("closed")
    assert emit_event({"event": "x"}, broken) == DELIVERY_FAILED


def test_drill_harness_is_anti_vacuous_and_never_targets_input_checkout():
    harness = Path(__file__).resolve().parents[3] / "scripts/drills/drill_vanished_file_tripwire.sh"
    text = harness.read_text()
    assert "git clone" in text and "mktemp -d" in text
    assert "EXIT_FILES_MISSING=10" in text
    assert "rm -- \"$scratch/$candidate\"" in text
