#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/develop/test_celery_worker_pool.py

"""Celery worker pool conformance gate for EVERY compose file.

SCOPE WIDENED 2026-09-06, and the reason is the point of this module. This
gate was written against the prod compose file alone. Seven weeks later the
cure had reached exactly ONE of the five compose files that define a celery
worker, and BOTH live stacks running an uncured file were wedged: dev with
225,119 messages queued on `celery` and 10,653 on `vis_queue`, staging with
428,902 and 32,795 — staging reporting "healthy" throughout, because only dev
had been given the execution-asserting healthcheck. A gate whose population is
a hardcoded list of the services someone remembered cannot catch the service
nobody remembered, so the population is now DISCOVERED from disk and floored.

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
PREFORK_ONLY_OPTIONS = ("-O/--optimization", "--max-tasks-per-child",
                        "--max-memory-per-child")

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


def _service_command(service: str, compose: Path = None) -> str:
    """Return one compose service's ``command`` as a normalised string.

    Keyed by service NAME so the two celery workers can never be confused
    for one another. Whitespace is collapsed because the compose file uses
    a folded (``>``) block scalar, which yields embedded newlines.
    """
    compose = PROD_COMPOSE if compose is None else compose
    spec = yaml.safe_load(compose.read_text(encoding="utf-8"))
    services = spec["services"]
    if service not in services:
        raise AssertionError(
            f"{compose.name} has no service {service!r}; "
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
                "--maxtasksperchild", "--max-memory-per-child",
                "--maxmemoryperchild")
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
        "--max-memory-per-child=500000",
        "--maxmemoryperchild=500000",
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



# ---------------------------------------------------------------------------
# WHOLE-POPULATION GATE
#
# Everything above keys on a hardcoded list of prod service names. That is
# what let four compose files drift: a gate can only protect the services
# someone thought to name in it. Below, the population is DISCOVERED from
# disk, so a compose file added tomorrow is covered the day it lands.
# ---------------------------------------------------------------------------

DEPLOYMENT_DIR = REPO_ROOT / "deployment"

# Measured 2026-09-06: six celery worker services across five compose files.
# Floors, not equalities, so adding a worker does not fail the suite -- but a
# discovery that silently returns NOTHING cannot pass, which is the failure
# mode that matters. Every per-worker assertion below is parametrized over
# this population, and a parametrize over an EMPTY list runs zero tests and
# reports success, which reads exactly like "all workers conform".
CELERY_WORKER_FLOOR = 6
CELERY_WORKER_FILE_FLOOR = 5


def _command_of(service_spec) -> str | None:
    """Return a service's ``command`` normalised to one line, or None."""
    if not isinstance(service_spec, dict):
        return None
    command = service_spec.get("command")
    if command is None:
        return None
    if isinstance(command, list):
        command = " ".join(str(part) for part in command)
    return " ".join(str(command).split())


def _discover_celery_workers() -> list[tuple[str, str, str]]:
    """Every (compose file, service, command) that runs a celery WORKER.

    A parse failure is raised, never skipped: a compose file this gate cannot
    read is a file it cannot protect, and silently passing over it is how the
    drift above happened in the first place.
    """
    found: list[tuple[str, str, str]] = []
    for path in sorted(DEPLOYMENT_DIR.rglob("*.yml")):
        if "compose" not in path.name:
            continue
        try:
            spec = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:  # pragma: no cover - defensive
            raise AssertionError(f"{path} did not parse as YAML: {exc}") from exc
        if not isinstance(spec, dict):
            continue
        for name, service_spec in (spec.get("services") or {}).items():
            command = _command_of(service_spec)
            if command and "celery" in command and " worker" in command:
                found.append(
                    (path.relative_to(REPO_ROOT).as_posix(), name, command)
                )
    return sorted(found)


_WORKERS = _discover_celery_workers()
_WORKER_IDS = [f"{rel}::{svc}" for rel, svc, _ in _WORKERS]


def test_discovery_finds_the_whole_celery_worker_population():
    """Floor the population, and name the files that MUST be in it.

    Two distinct failures are guarded. A discovery returning zero would make
    every parametrized assertion below vacuous. A discovery returning only
    SOME files -- the actual 2026-09-06 defect, where only the prod file was
    ever checked -- would leave the rest drifting while the suite stayed
    green, so the three environments are named explicitly.
    """
    # Arrange
    must_include = (
        "deployment/docker/docker_dev/docker-compose.yml",
        "deployment/docker/docker-compose.staging.yml",
        "deployment/docker/docker_prod/docker-compose.yml",
    )
    # Act
    files = {rel for rel, _, _ in _WORKERS}
    missing = [f for f in must_include if f not in files]
    # Assert
    assert (
        len(_WORKERS) >= CELERY_WORKER_FLOOR
        and len(files) >= CELERY_WORKER_FILE_FLOOR
        and not missing
    ), (
        f"expected >={CELERY_WORKER_FLOOR} celery workers across "
        f">={CELERY_WORKER_FILE_FLOOR} compose files including {must_include!r}; "
        f"found {len(_WORKERS)} across {len(files)}, missing={missing!r}, "
        f"files={sorted(files)}"
    )


@pytest.mark.parametrize("relpath,service,command", _WORKERS, ids=_WORKER_IDS)
def test_every_celery_worker_asks_for_the_threads_pool(relpath, service, command):
    """Prefork wedges on this host — no compose file may ship it.

    Stated as a conjunction with ``--queues=``: without that positive term a
    command that failed to parse into anything would satisfy the real
    assertion for free.
    """
    # Assert
    assert "--queues=" in command and "--pool=threads" in command, (
        f"{relpath}::{service} must carry a --queues= selector (proving a real "
        f"celery worker command was parsed) AND --pool=threads (prefork wedges "
        f"on this host — see this module's docstring); got: {command!r}"
    )


@pytest.mark.parametrize("relpath,service,command", _WORKERS, ids=_WORKER_IDS)
def test_every_celery_worker_drops_prefork_only_flags(relpath, service, command):
    """Dead prefork config must not survive the switch, in any file."""
    # Act
    leftover = _prefork_only_tokens(command)
    # Assert
    assert (
        "--queues=" in command
        and "--pool=threads" in command
        and not leftover
    ), (
        f"{relpath}::{service} must be a threads-pool worker carrying none of "
        f"{list(PREFORK_ONLY_OPTIONS)}; leftover={leftover!r}; "
        f"command={command!r}"
    )


@pytest.mark.parametrize("relpath,service,command", _WORKERS, ids=_WORKER_IDS)
def test_every_celery_worker_keeps_pool_agnostic_flags(relpath, service, command):
    """The flags the pool switch does not replace must survive everywhere."""
    # Act
    missing = [flag for flag in POOL_AGNOSTIC_FLAGS if flag not in command]
    # Assert
    assert not missing, (
        f"{relpath}::{service} lost {missing!r}; --prefetch-multiplier and the "
        f"three --without-* flags are pool-agnostic and must survive the "
        f"switch; command={command!r}"
    )


def test_worker_discovery_ignores_beat_and_non_celery_services():
    """Negative control: the discovery predicate must not match everything.

    ``celery ... beat`` is a scheduler, not a worker, and must never be held
    to the worker pool rule. A predicate that matched it would also match any
    future celery subcommand, making the population meaningless.
    """
    # Arrange
    beat = {
        "command": "celery -A config --broker=redis://redis:6379/1 beat "
                   "--loglevel=info"
    }
    worker = {
        "command": "celery -A config worker --queues=celery --pool=threads"
    }
    # Act
    beat_command = _command_of(beat)
    worker_command = _command_of(worker)
    # Assert
    assert (
        beat_command is not None
        and " worker" not in beat_command
        and worker_command is not None
        and " worker" in worker_command
    ), (
        f"the worker predicate must separate beat from worker; "
        f"beat={beat_command!r}; worker={worker_command!r}"
    )


# EOF
