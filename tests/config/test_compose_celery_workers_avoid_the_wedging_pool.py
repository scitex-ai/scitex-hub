#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Every celery worker must declare ``--pool=threads``. Prefork wedges here.

WHY THIS TEST EXISTS. The celery PREFORK pool wedges on this host. The failure
was measured three separate times — 2026-07-14, 2026-07-17 and 2026-07-30 — and
the full diagnosis lives above ``celery_worker`` in
``deployment/docker/docker_prod/docker-compose.yml``, which is the authority
for the mechanism. In short: a worker processes roughly one prefetch window and
then dispatch dies. ``inspect reserved`` shows a full window that never runs,
``inspect active`` is empty, the fork children exist and idle, the control
channel still answers, redis still pings, and the container reports healthy
throughout. A restart drains one burst and wedges again.

FIVE fixes were tried against that signature and all five failed (#379 tini as
PID 1, #381 ``-O fair`` + max-tasks-per-child, #384 the celery<5.6 pin plus
--without-gossip/mingle/heartbeat). It reproduces on celery 5.5.3 and 5.6.3.
The differential that settles it varies ONE thing: the same container, code,
broker and queue with ``--pool=threads`` drains immediately — 48 tasks in 200s
on vis_queue where prefork never exceeded 6.

PROD WAS FIXED ON 2026-07-30 AND NOTHING ELSE WAS. Measured 2026-09-05: the dev
worker had executed zero tasks in 12.9 hours with celery at 212k messages and
vis_queue at 9.9k, unacked=0, while docker reported "healthy". The visitor pool
depends on that worker to un-quarantine slots, so the visitor experience was
dead for hours and a human noticed first.

That is the SECOND time in one evening that the pattern was "prod diagnosed it,
fixed it, and no other compose file was migrated" — the first being the queue
liveness healthcheck (see test_compose_celery_workers_assert_execution.py,
same July fortnight, same worker). A prose diagnosis sitting in one
environment's compose file did not propagate for seven weeks. This is a gate so
that it cannot fail to propagate a third time.

WHY THREADS ARE SAFE FOR THESE QUEUES. matplotlib is not thread-safe and was
reachable via server-side chart rendering; that moved client-side (operator
direction, 2026-07-30), removing the sole constraint. It is not an assumption
here: prod already runs ALL of these queues on threads — celery_worker takes
celery/ai_queue/search_queue/compute_queue and celery_worker_vis takes
vis_queue, both ``--pool=threads``.

WHY THIS FILE LIVES UNDER ``tests/config/``. Same reason as its siblings —
PS-302 masks a fixed list of legacy ``tests/`` subdirectories, so a new
top-level one raises the audit ratchet. See the note in
``test_compose_entrypoints_keep_tini.py``.
"""

from __future__ import annotations

import pytest
import yaml

from ._compose_helpers import (
    MIN_EXPECTED_COMPOSE_FILES,
    REPO_ROOT,
    compose_files,
)

WEDGING_POOL_DEFAULT = "--pool="
REQUIRED_POOL = "--pool=threads"

# Recycle POOL CHILD PROCESSES. Under threads they do nothing, so leaving them
# advertises a recycling behaviour the worker does not have.
PREFORK_ONLY_FLAGS = ("--max-tasks-per-child", "--max-memory-per-child")


def worker_commands():
    """(file, service, command) for every celery worker that declares one.

    Discovered, not enumerated. A compose file that cannot be parsed is yielded
    as a service failing every rule rather than dropping out of the sweep.

    Only services declaring their own ``command`` are judged: compose MERGES an
    override onto its base, so a partial override that sets only, say,
    ``healthcheck.start_period`` inherits its command and is judged where that
    command is actually written. Failing it here would be a false positive on a
    correct file, and a gate that cries wolf gets switched off.
    """
    found = []
    for path in compose_files():
        try:
            document = yaml.safe_load(path.read_text()) or {}
            services = document.get("services") or {}
        except Exception:
            found.append((path, "<unparseable>", ""))
            continue
        for name, service in services.items():
            if not name.startswith("celery_worker"):
                continue
            if not isinstance(service, dict):
                continue
            command = str(service.get("command") or "")
            if "worker" not in command:
                continue
            found.append((path, name, command))
    return found


def test_discovery_found_the_compose_files():
    """Control: a glob matching nothing would pass every rule below vacuously."""
    # Arrange
    floor = MIN_EXPECTED_COMPOSE_FILES
    # Act
    discovered = compose_files()
    # Assert
    assert len(discovered) >= floor


def test_every_stack_declares_a_worker_command():
    """Control: the judged population must not silently empty.

    Measured 2026-09-05: 6 celery workers declare a command across 5 stacks.
    The floor sits below that deliberately — a tripwire for "discovery broke",
    not a headcount to edit whenever a stack is added or retired.
    """
    # Arrange
    floor = 5
    # Act
    workers = worker_commands()
    # Assert
    assert len(workers) >= floor


@pytest.mark.parametrize(
    "path,name,command",
    worker_commands(),
    ids=lambda value: getattr(value, "name", str(value))[:40],
)
def test_worker_declares_the_threads_pool(path, name, command):
    """An omitted --pool is the DEFAULT prefork, which is the wedging one."""
    # Arrange
    where = f"{path.relative_to(REPO_ROOT)}::{name}"
    # Act
    declared = REQUIRED_POOL in command
    # Assert
    assert declared, (
        f"{where} does not declare {REQUIRED_POOL}. Omitting --pool selects "
        "prefork, which wedges on this host (measured 2026-07-14/17/30; see "
        "the diagnosis above celery_worker in docker_prod/docker-compose.yml). "
        "A wedged worker reports healthy and runs nothing."
    )


@pytest.mark.parametrize(
    "path,name,command",
    worker_commands(),
    ids=lambda value: getattr(value, "name", str(value))[:40],
)
def test_worker_carries_no_prefork_only_flags(path, name, command):
    """Child-recycling flags do nothing under threads; keeping them misleads."""
    # Arrange
    where = f"{path.relative_to(REPO_ROOT)}::{name}"
    # Act
    stale = [flag for flag in PREFORK_ONLY_FLAGS if flag in command]
    # Assert
    assert not stale, (
        f"{where} still passes {stale}, which recycle POOL CHILD PROCESSES and "
        "have no effect under --pool=threads. Remove them rather than leaving "
        "a memory-recycling promise the worker cannot keep."
    )


# EOF
