#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/develop/test_celery_worker_pool.py

"""Celery worker pool conformance gate for the prod compose file.

The PREFORK pool wedges on the prod host. Measured signature (2026-07-14,
2026-07-17 and again 2026-07-30): ``celery inspect reserved`` shows a FULL
prefetch window with ``worker_pid=None`` / ``time_start=None`` /
``acknowledged=false``, ``inspect active`` is EMPTY, the fork children stay
alive and idle, the control channel still answers, redis still pings, and
the container reports ``(healthy)`` throughout. FIVE fixes were tried
against it and all five failed: tini restored as PID 1 (#379), ``-O fair``
plus ``--max-tasks-per-child`` (#381), and the ``celery<5.6`` pin with
``--without-gossip/mingle/heartbeat`` (#384).

The differential experiment that settled it, run twice: an ad-hoc worker in
the SAME container, same code, same broker, same queue, differing ONLY by
``--pool=threads``, drains immediately (2026-07-17 vis_queue: 48 tasks in
200s where prefork never exceeded 6; 2026-07-30 default queue:
``collect_server_metrics`` succeeded in 0.131s and ``ServerMetrics``' newest
row jumped forward 2.5 hours within 90s). The tasks are fine and fast; the
POOL is the defect.

So both prod celery workers must run ``--pool=threads``, and must NOT carry
the two PREFORK-ONLY flags — ``-O fair`` (a prefork child-dispatch strategy)
and ``--max-tasks-per-child`` (recycles fork children, of which a threads
pool has none). Celery ignores both under ``--pool=threads``, so leaving
them in place is dead configuration that reads as an active mitigation for
exactly the wedge they failed to fix.

Every assertion here is stated as a single CONJUNCTION pairing the negative
term with a positive control on the SAME parsed object, because "``-O fair``
is absent" passes for free if the YAML parse returned nothing, the service
key was renamed, or the wrong file was read. And the command is looked up
PER SERVICE by name, never substring-matched over the whole file:
``celery_worker_vis`` has carried ``--pool=threads`` since #385, so a
whole-file match would pass on the vis worker's flags while the shared
worker stayed prefork.
"""

from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
PROD_COMPOSE = (
    REPO_ROOT / "deployment" / "docker" / "docker_prod" / "docker-compose.yml"
)

# Human-readable name for the two prefork-only options, for messages. The
# actual detection is _prefork_only_tokens(), which matches every spelling
# rather than one literal — see its docstring.
PREFORK_ONLY_OPTIONS = ("-O/--optimization", "--max-tasks-per-child")

# Flags that must survive the switch: the QoS window that keeps a worker
# from hoarding the queue, and the three kombu-async-hub features that are
# pure overhead for a fixed two-worker deployment (celery#8091).
POOL_AGNOSTIC_FLAGS = (
    "--prefetch-multiplier=1",
    "--without-gossip",
    "--without-mingle",
    "--without-heartbeat",
)

# Each prod worker and the queue selector that identifies it. The queue
# selector is the POSITIVE CONTROL: it is unique per service, so it proves
# the assertion read THAT service's command and not the sibling's.
WORKER_QUEUE_MARKERS = {
    "celery_worker": "--queues=celery,ai_queue,search_queue,compute_queue",
    "celery_worker_vis": "--queues=vis_queue",
}


def _service_command(service: str) -> str:
    """Return one compose service's ``command`` as a normalised string.

    Keyed by service NAME so the two celery workers can never be confused
    for one another. Whitespace is collapsed because the compose file uses
    a folded (``>``) block scalar, which yields embedded newlines.
    """
    spec = yaml.safe_load(PROD_COMPOSE.read_text(encoding="utf-8"))
    services = spec["services"]
    if service not in services:
        raise AssertionError(
            f"prod compose has no service {service!r}; "
            f"found: {sorted(services)}"
        )
    command = services[service]["command"]
    if isinstance(command, list):
        command = " ".join(command)
    return " ".join(command.split())


def _prefork_only_tokens(command: str) -> list[str]:
    """Return every prefork-only option token present in ``command``.

    Matched by SHAPE, not by one literal string, because a negative
    assertion keyed on a single spelling passes vacuously the moment the
    flag comes back under another one — and celery's worker CLI accepts
    several for both options:

    * ``-O fair``, ``-Ofair``, ``--optimization=fair``,
      ``--optimization fair``
    * ``--max-tasks-per-child=N``, ``--maxtasksperchild=N``

    Any token beginning ``-O`` is the optimization flag (no other celery
    worker short option starts with a capital O), and any token beginning
    ``--optimization`` / ``--max-tasks-per-child`` / ``--maxtasksperchild``
    is one of the two long forms.
    """
    prefixes = ("-O", "--optimization", "--max-tasks-per-child",
                "--maxtasksperchild")
    return [t for t in command.split() if t.startswith(prefixes)]


@pytest.mark.parametrize("service", sorted(WORKER_QUEUE_MARKERS))
def test_prod_celery_worker_asks_for_the_threads_pool(service):
    """Pass only if this service's OWN command asks for --pool=threads."""
    # Arrange
    queue_marker = WORKER_QUEUE_MARKERS[service]
    # Act
    command = _service_command(service)
    # Assert
    assert queue_marker in command and "--pool=threads" in command, (
        f"{service} must carry {queue_marker!r} (proving this assertion read "
        f"the right service) AND --pool=threads (the prefork pool wedges on "
        f"the prod host — see this module's docstring); got: {command!r}"
    )


@pytest.mark.parametrize("service", sorted(WORKER_QUEUE_MARKERS))
def test_prod_celery_worker_drops_prefork_only_flags(service):
    """No prefork-only flag may be left behind on a threads-pool worker.

    Pass condition, as one conjunction: the parsed command belongs to
    ``service`` (its unique ``--queues=`` selector is present) AND it asks
    for ``--pool=threads`` AND none of the prefork-only flags remain. The
    two positive terms exist so that a bad parse, a renamed service key or
    a wrong file path fails LOUD instead of satisfying the negative term
    vacuously.
    """
    # Arrange
    queue_marker = WORKER_QUEUE_MARKERS[service]
    # Act
    command = _service_command(service)
    leftover = _prefork_only_tokens(command)
    # Assert
    assert (
        queue_marker in command
        and "--pool=threads" in command
        and not leftover
    ), (
        f"{service} must carry {queue_marker!r} and --pool=threads, and must "
        f"carry none of {list(PREFORK_ONLY_OPTIONS)}; leftover={leftover!r}; "
        f"command={command!r}"
    )


@pytest.mark.parametrize("service", sorted(WORKER_QUEUE_MARKERS))
def test_prod_celery_worker_keeps_pool_agnostic_flags(service):
    """The pool switch must not quietly drop the flags it does not replace."""
    # Arrange
    expected = (WORKER_QUEUE_MARKERS[service], *POOL_AGNOSTIC_FLAGS)
    # Act
    command = _service_command(service)
    missing = [flag for flag in expected if flag not in command]
    # Assert
    assert not missing, (
        f"{service} lost {missing!r} — the --queues selector, "
        f"--prefetch-multiplier and the three --without-* flags are all "
        f"pool-agnostic and must survive; command={command!r}"
    )


def test_prod_celery_workers_do_not_share_one_command():
    """Guard the guard: prove per-service keying, not whole-file matching.

    ``celery_worker_vis`` has carried ``--pool=threads`` since #385. If the
    lookup above ever degrades into a substring match over the whole compose
    file, every assertion in this module would pass on the vis worker's
    flags while the shared worker silently stayed prefork. Requiring that
    each command own its OWN queue selector and NOT the sibling's makes that
    degradation fail here first.
    """
    # Arrange
    shared_marker = WORKER_QUEUE_MARKERS["celery_worker"]
    vis_marker = WORKER_QUEUE_MARKERS["celery_worker_vis"]
    # Act
    shared = _service_command("celery_worker")
    vis = _service_command("celery_worker_vis")
    # Assert
    assert (
        shared_marker in shared
        and vis_marker not in shared
        and vis_marker in vis
        and shared_marker not in vis
    ), (
        "each prod celery worker must own its OWN queue selector and not the "
        f"sibling's; celery_worker={shared!r}; celery_worker_vis={vis!r}"
    )


@pytest.mark.parametrize(
    "spelling",
    [
        "-O fair",
        "-Ofair",
        "--optimization=fair",
        "--optimization fair",
        "--max-tasks-per-child=50",
        "--maxtasksperchild=50",
    ],
)
def test_prefork_flag_detector_catches_every_celery_spelling(spelling):
    """Positive control on the DETECTOR, so the negative cannot go vacuous.

    ``test_prod_celery_worker_drops_prefork_only_flags`` asserts an ABSENCE,
    and an absence check keyed on one literal spelling silently stops
    protecting anything the moment the flag returns under a different one —
    celery's CLI accepts `-O fair`, `-Ofair`, `--optimization=fair`,
    `--optimization fair`, `--max-tasks-per-child` and `--maxtasksperchild`.
    Feeding each spelling to the detector proves it actually fires, rather
    than trusting that a `not in` over the real file means what we hope.
    """
    # Arrange
    command = f"celery -A config worker --queues=celery {spelling}"
    # Act
    detected = _prefork_only_tokens(command)
    # Assert
    assert detected, (
        f"the prefork-flag detector missed {spelling!r} — the absence "
        f"assertion it backs would pass vacuously for this spelling; "
        f"command={command!r}"
    )


def test_prefork_flag_detector_ignores_the_flags_we_keep():
    """Negative control on the detector: it must not cry wolf.

    A detector that flags everything would make the absence assertion
    unsatisfiable, and the obvious "fix" would be to weaken it back to a
    single literal. Pin that it passes the flags this PR deliberately KEEPS.
    """
    # Arrange
    command = (
        "celery -A config --broker=redis://redis:6379/1 worker "
        "--loglevel=info --queues=celery,ai_queue --pool=threads "
        "--concurrency=8 --prefetch-multiplier=1 --without-gossip "
        "--without-mingle --without-heartbeat"
    )
    # Act
    detected = _prefork_only_tokens(command)
    # Assert
    assert not detected, (
        f"the detector flagged {detected!r} in a command that carries only "
        f"pool-agnostic flags; command={command!r}"
    )


# EOF
