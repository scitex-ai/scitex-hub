#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/config/test_pgbouncer_healthcheck_proves_a_client_can_connect.py

"""Every pgbouncer healthcheck must COMPLETE a connection, not ping a port.

`pg_isready` is libpq's PQping, and PQping returns OK whenever the server
RESPONDS -- including when it responds with a rejection. Measured 2026-09-06
against the staging pooler (edoburu/pgbouncer:v1.25.1-p0, the image prod also
runs), exit codes:

                         psql -c 'select 1'      pg_isready
    good credentials             0                    0
    wrong password               2                    0
    unreachable port             2                    0

The middle row is the finding. A user that does not exist and a database that
does not exist BOTH report "accepting connections" and exit 0, so adding
``-U``/``-d`` to pg_isready buys nothing -- it produces a check that LOOKS
authenticated and measures exactly what it measured before.

This is not hypothetical. On 2026-09-06 prod's pooler refused EVERY client
connection for ~6 minutes (``pooler error: unsupported startup parameter in
options: statement_timeout``, 365 rejections, /auth/login/ 500 throughout) and
its healthcheck reported ``healthy`` for the entire outage. The outage was
diagnosed from a log grep because every instrument designed to report health
said fine.

TWO PROPERTIES ARE ASSERTED, and the second is the one that is easy to lose.

1. The probe must AUTHENTICATE and QUERY -- psql running a statement, not a
   ping. That is what makes the check able to fail at all (see the table).

2. The probe must send the SAME startup parameters Django sends. The outage's
   rejection was triggered by Django's ``options: -c statement_timeout=30000``;
   pg_isready never sends ``options``, so no variant of it could reproduce the
   failure. A probe that authenticates but omits ``options`` would have stayed
   green through that outage too. The parameter list is therefore checked
   against config/settings/ rather than hardcoded here, reusing the parser from
   test_pgbouncer_tracks_every_option_django_sends so the two gates cannot
   disagree about what Django sends.

The population is DISCOVERED from disk and floored, not listed. A sibling gate
(tests/develop/test_celery_worker_pool.py) was scoped to one compose file by
construction, and four other files drifted for seven weeks underneath it while
it stayed green. A hardcoded population is how that happens.
"""

from pathlib import Path

import pytest
import yaml

from .test_pgbouncer_tracks_every_option_django_sends import sent_parameters

REPO_ROOT = Path(__file__).resolve().parents[2]
DEPLOYMENT_DIR = REPO_ROOT / "deployment"

# Measured 2026-09-06: two pgbouncer healthchecks, in two compose files.
# Floors, not equalities -- adding a pooler must not fail the suite, but a
# discovery that returns NOTHING must, because a parametrize over an empty
# list runs zero tests and reports success, which reads like conformance.
PGBOUNCER_HEALTHCHECK_FLOOR = 2

# Named explicitly so a discovery that finds SOME files cannot pass. Partial
# discovery is the failure mode that floors alone do not catch.
MUST_INCLUDE = (
    "deployment/docker/docker-compose.yml",
    "deployment/docker/docker_prod/docker-compose.yml",
)


def _healthcheck_test(service_spec) -> str | None:
    """Return a service's healthcheck test, normalised to one string."""
    if not isinstance(service_spec, dict):
        return None
    healthcheck = service_spec.get("healthcheck")
    if not isinstance(healthcheck, dict):
        return None
    test = healthcheck.get("test")
    if test is None:
        return None
    if isinstance(test, list):
        test = " ".join(str(part) for part in test)
    return " ".join(str(test).split())


def _discover_pgbouncer_healthchecks() -> list[tuple[str, str]]:
    """Every (compose file, healthcheck test) for a pgbouncer service.

    A compose file that does not parse is raised, never skipped: a file this
    gate cannot read is a file it cannot protect.
    """
    found: list[tuple[str, str]] = []
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
            if "pgbouncer" not in name:
                continue
            test = _healthcheck_test(service_spec)
            if test:
                found.append((path.relative_to(REPO_ROOT).as_posix(), test))
    return sorted(found)


def _is_port_ping_only(test: str) -> bool:
    """True when the probe only pings, i.e. cannot observe a refusal.

    Keyed on what the probe DOES (pg_isready with no query) rather than on one
    literal spelling, so `-U`/`-d` variants -- which measure exactly the same
    thing, per this module's docstring -- are still caught.
    """
    return "pg_isready" in test and "psql" not in test


_HEALTHCHECKS = _discover_pgbouncer_healthchecks()
_IDS = [rel for rel, _ in _HEALTHCHECKS]


def test_discovery_finds_every_pgbouncer_healthcheck():
    """Floor the population and name the files that must be in it."""
    # Arrange
    expected_floor = PGBOUNCER_HEALTHCHECK_FLOOR
    # Act
    files = {rel for rel, _ in _HEALTHCHECKS}
    missing = [f for f in MUST_INCLUDE if f not in files]
    # Assert
    assert (
        len(_HEALTHCHECKS) >= expected_floor and not missing
    ), (
        f"expected >={expected_floor} pgbouncer healthchecks "
        f"including {MUST_INCLUDE!r}; found {len(_HEALTHCHECKS)}, "
        f"missing={missing!r}, files={sorted(files)}"
    )


@pytest.mark.parametrize("relpath,test", _HEALTHCHECKS, ids=_IDS)
def test_pgbouncer_healthcheck_completes_a_connection(relpath, test):
    """Pass only if the probe authenticates and runs a statement.

    Stated as a conjunction with `6432`: without that positive term, a
    healthcheck that failed to parse into anything would satisfy the psql
    requirement vacuously.
    """
    # Arrange
    port_marker = "6432"
    # Act
    ping_only = _is_port_ping_only(test)
    # Assert
    assert (
        port_marker in test
        and "psql" in test
        and not ping_only
    ), (
        f"{relpath}: the pgbouncer healthcheck must COMPLETE a connection "
        f"(psql running a statement against 6432), not ping the port -- "
        f"pg_isready exits 0 for a nonexistent user AND database, so it "
        f"cannot observe a pooler refusing every client; got: {test!r}"
    )


@pytest.mark.parametrize("relpath,test", _HEALTHCHECKS, ids=_IDS)
def test_pgbouncer_healthcheck_sends_what_django_sends(relpath, test):
    """The probe must carry every startup parameter Django carries.

    A probe that authenticates but omits `options` would have stayed GREEN
    through the 2026-09-06 outage, because that outage's rejection was
    triggered by `options` and nothing else. The expected list comes from
    config/settings/, so adding a parameter there fails here until the probe
    sends it too.
    """
    # Arrange
    expected = sent_parameters()
    # Act
    missing = [param for param in expected if param not in test]
    # Assert
    assert expected and not missing, (
        f"{relpath}: the healthcheck must send the same startup parameters "
        f"Django does (from config/settings/): expected {sorted(expected)}, "
        f"missing {missing!r}. Without them the probe cannot reproduce the "
        f"refusal it exists to catch; got: {test!r}"
    )


@pytest.mark.parametrize(
    "probe,expected_ping_only",
    [
        ('CMD pg_isready -h localhost -p 6432', True),
        ('CMD-SHELL pg_isready -h localhost -p 6432 -U scitex -d scitex_hub', True),
        ('CMD-SHELL PGPASSWORD="x" psql -h 127.0.0.1 -p 6432 -tAc \'select 1\'', False),
    ],
)
def test_the_ping_only_detector_is_calibrated(probe, expected_ping_only):
    """Positive AND negative control on the detector.

    The middle row is the one that matters: `pg_isready -U ... -d ...` LOOKS
    like a credentialed check and measures the same thing as the bare form
    (both exit 0 for a nonexistent user), so a detector that passed it would
    green-light the exact non-fix this card rejected.
    """
    # Arrange
    probe_under_test = probe
    # Act
    detected = _is_port_ping_only(probe_under_test)
    # Assert
    assert detected is expected_ping_only, (
        f"detector said ping_only={detected} for {probe_under_test!r}, "
        f"expected {expected_ping_only}"
    )


# EOF
