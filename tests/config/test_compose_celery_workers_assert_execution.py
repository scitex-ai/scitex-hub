#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Every celery worker healthcheck must prove EXECUTION, not connectivity.

WHY THIS TEST EXISTS. A celery worker can hold its broker connection, answer
``inspect ping`` on the control channel, and keep its fork children alive while
dispatching NOTHING. A ``redis.ping()`` healthcheck stays green through the
whole outage, because it measures the broker rather than the worker.

That is why ``deployment/docker/common/scripts/check_queue_liveness.sh`` exists:
it reads the ``scitex:liveness:<queue>`` stamp that ``queue_liveness_beacon``
writes at EXECUTION time, so only a worker that actually ran a task can be
healthy. It was written 2026-07-17 after a measured prod wedge.

IT WAS ONLY EVER WIRED INTO PROD. Measured 2026-09-05: every other compose file
still had the ping, and the dev worker had executed nothing for 12.9 hours while
docker reported ``Up 7 hours (healthy)``. Running prod's own script against that
container returned, immediately::

    UNHEALTHY: queue 'celery' - last beacon executed 46499s ago (budget 600s)

So the detector existed, was correct, and was pointed at one environment out of
five. The visitor pool sat quarantined for 2h45m behind a green checkmark and
the thing that eventually noticed was a human looking at a browser.

A COMMENT WOULD NOT HAVE HELD THIS. The script's own header explains the failure
mode in detail, and the four files that needed it were edited many times since
July without anyone applying it. The rule has to be a gate, because the drift is
silent in exactly the direction that looks fine.

WHY BEAT IS NOT COVERED. Beat's job is to SCHEDULE, and its failure already
surfaces here: no beat means no beacon is enqueued, the stamps go stale, and
every worker watching them goes unhealthy. Asserting a second, independent
liveness mechanism on beat would be inventing a rule for a failure nobody has
measured. Prod made the same call.

WHY THIS FILE LIVES UNDER ``tests/config/``. Same reason as its siblings --
PS-302 masks a fixed list of legacy ``tests/`` subdirectories, so adding a new
top-level one raises the audit ratchet. See the note in
``test_compose_entrypoints_keep_tini.py``.
"""

from __future__ import annotations

import re

import pytest
import yaml

from ._compose_helpers import (
    MIN_EXPECTED_COMPOSE_FILES,
    REPO_ROOT,
    compose_files,
)

LIVENESS_SCRIPT = "check_queue_liveness.sh"
CONNECTIVITY_ONLY = "r.ping()"

SETTINGS_CELERY = REPO_ROOT / "config" / "settings" / "settings_celery.py"

# A beacon entry looks like:
#     "queue-liveness-beacon-celery": {
#         "task": "apps.infra.public_app.tasks.queue_liveness_beacon",
#         "args": ["celery"],
BEACON_ARGS = re.compile(
    r"queue_liveness_beacon\"\s*,\s*.*?\"args\"\s*:\s*\[\s*\"([a-z_]+)\"\s*\]",
    re.S,
)


def beaconed_queues():
    """Queues beat actually stamps, read from the beat schedule.

    Derived rather than hardcoded so that a queue added to (or dropped from)
    ``CELERY_BEAT_SCHEDULE`` without the matching healthcheck change fails
    here, which is the drift this gate exists to catch.
    """
    return sorted(set(BEACON_ARGS.findall(SETTINGS_CELERY.read_text())))


def worker_services():
    """(file, service_name, service) for every celery worker DECLARING a test.

    Discovered, not enumerated. A compose file that cannot be parsed is yielded
    as a service that fails every rule rather than dropping silently out of the
    sweep -- an unparseable file must never read as clean.

    ONLY SERVICES THAT DECLARE ``healthcheck.test`` ARE JUDGED, because compose
    MERGES an override onto its base. ``docker_dev/docker-compose.override.yml``
    sets ``celery_worker.healthcheck.start_period`` and nothing else; the
    effective ``test:`` comes from the base file and is judged there. Verified
    on the running container 2026-09-05 -- ``docker inspect`` showed the base
    file's test on a worker whose override names only start_period. Treating
    that partial override as "no execution proof" is a false positive, and a
    gate that cries wolf on a correct file gets switched off.

    The consequence is deliberate: a worker with NO healthcheck anywhere is not
    caught here. That is a different defect (no gate at all, rather than a gate
    that cannot fail), and ``test_every_stack_declares_worker_healthchecks``
    below keeps the judged population from silently emptying.
    """
    found = []
    for path in compose_files():
        try:
            document = yaml.safe_load(path.read_text()) or {}
            services = document.get("services") or {}
        except Exception:
            found.append((path, "<unparseable>", {}))
            continue
        for name, service in services.items():
            if not name.startswith("celery_worker"):
                continue
            if not isinstance(service, dict):
                continue
            if (service.get("healthcheck") or {}).get("test") is None:
                continue
            found.append((path, name, service))
    return found


def healthcheck_test(service):
    return str((service.get("healthcheck") or {}).get("test") or "")


def consumed_queues(service):
    command = str(service.get("command") or "")
    match = re.search(r"--queues=([\w,]+)", command)
    return match.group(1).split(",") if match else []


def test_discovery_found_the_compose_files():
    """Control: a glob matching nothing would pass every rule below vacuously."""
    # Arrange
    floor = MIN_EXPECTED_COMPOSE_FILES
    # Act
    discovered = compose_files()
    # Assert
    assert len(discovered) >= floor


def test_every_stack_declares_worker_healthchecks():
    """Control: the judged population must not silently empty.

    ``worker_services`` skips partial overrides that declare no ``test:``. If
    that filter ever widened -- or a stack stopped declaring healthchecks at
    all -- every rule below would pass vacuously. Measured 2026-09-05: 6
    declaring workers across 5 stacks. The floor sits below that deliberately;
    it is a tripwire, not a headcount to edit whenever a stack is added.
    """
    # Arrange
    floor = 5
    # Act
    workers = worker_services()
    # Assert
    assert len(workers) >= floor


def test_beat_schedule_declares_beaconed_queues():
    """Control: a broken parse here would excuse every worker below."""
    # Arrange
    # Act
    queues = beaconed_queues()
    # Assert
    assert len(queues) >= 2


@pytest.mark.parametrize(
    "path,name,service",
    worker_services(),
    ids=lambda value: getattr(value, "name", str(value))[:40],
)
def test_worker_healthcheck_is_not_connectivity_only(path, name, service):
    """A broker ping stays green through a total dispatch wedge."""
    # Arrange
    where = f"{path.relative_to(REPO_ROOT)}::{name}"
    # Act
    test = healthcheck_test(service)
    # Assert
    assert CONNECTIVITY_ONLY not in test, (
        f"{where} pings the broker. That stays green through a total dispatch "
        f"wedge -- use {LIVENESS_SCRIPT}, which proves a task executed."
    )


@pytest.mark.parametrize(
    "path,name,service",
    worker_services(),
    ids=lambda value: getattr(value, "name", str(value))[:40],
)
def test_worker_healthcheck_proves_execution(path, name, service):
    """Some proof-of-execution must be wired in at all."""
    # Arrange
    where = f"{path.relative_to(REPO_ROOT)}::{name}"
    # Act
    test = healthcheck_test(service)
    # Assert
    assert LIVENESS_SCRIPT in test, (
        f"{where} has no execution proof in its healthcheck: {test!r}"
    )


@pytest.mark.parametrize(
    "path,name,service",
    worker_services(),
    ids=lambda value: getattr(value, "name", str(value))[:40],
)
def test_worker_healthcheck_watches_every_beaconed_queue_it_serves(
    path, name, service
):
    """A worker draining one queue while starving another is not healthy.

    Only queues the worker actually consumes AND beat actually stamps are
    required: asserting a stamp nobody writes would fail a correct worker
    forever.
    """
    # Arrange
    where = f"{path.relative_to(REPO_ROOT)}::{name}"
    test = healthcheck_test(service)
    consumed = consumed_queues(service)
    stamped = beaconed_queues()
    # Act
    missing = [
        queue for queue in stamped if queue in consumed and queue not in test
    ]
    # Assert
    assert not missing, (
        f"{where} consumes {consumed} and beat stamps {stamped}, but its "
        f"healthcheck never checks {missing}. A wedge on those queues would "
        "report healthy."
    )


# EOF
