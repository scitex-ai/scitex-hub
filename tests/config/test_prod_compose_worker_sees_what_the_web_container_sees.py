#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The prod celery worker must see the local bibliographic databases the web container sees.

``warm_public_status_cache`` runs in ``celery_worker`` (celery beat schedules
it; the ``celery`` queue executes it) and computes the public /status/ page's
verdicts by calling ``crossref_local.info()`` and ``openalex_local.info()``.
Those packages open the SQLite files named by ``CROSSREF_LOCAL_DB`` and
``OPENALEX_LOCAL_DB``. On 2026-09-05 production showed both as "Degraded" for a
day because the worker had neither the /data mounts nor the variables: the
django container read both databases fine, and the page reported the worker's
blind spot as degradation.

The rule is parity, not a fixed path: whatever the ``django`` service mounts at
/data/crossref and /data/openalex, and whatever it sets the four LOCAL_* vars
to, ``celery_worker`` must mount and set identically. A future change to the
source path then updates both or fails here — the same shape as the
sections.sh registry: one fact, one place.

WHAT EACH TEST IS FOR
  django_mounts_both_databases      the control: the parity assertions below
                                    are vacuous if the web container itself
                                    stopped mounting them.
  worker_mounts_the_same_*          target-for-target identity of the two
                                    bind mounts, source path included.
  worker_sets_the_same_local_db_env the four variables, value for value.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[2]
COMPOSE = REPO / "deployment" / "docker" / "docker_prod" / "docker-compose.yml"

LOCAL_DB_TARGETS = ("/data/crossref", "/data/openalex")
LOCAL_DB_ENV = (
    "CROSSREF_LOCAL_DB",
    "CROSSREF_LOCAL_MODE",
    "OPENALEX_LOCAL_DB",
    "OPENALEX_LOCAL_MODE",
)


@pytest.fixture(name="services", scope="module")
def _services() -> dict:
    return yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))["services"]


def _mounts_by_target(service: dict) -> dict[str, str]:
    """Map container target -> full volume spec for a service's bind mounts.

    Parsed from the RIGHT: a source such as ``${OPENALEX_LOCAL_DB_DIR:-/home/x}``
    carries its own colon, so splitting from the left names the wrong target
    (measured: the first version of this file failed its own control on it).
    """
    out: dict[str, str] = {}
    for spec in service.get("volumes", []):
        if not isinstance(spec, str) or ":" not in spec:
            continue
        rest = spec
        if rest.endswith((":ro", ":rw", ":z", ":Z")):
            rest = rest.rsplit(":", 1)[0]
        if ":" not in rest:
            continue
        target = rest.rsplit(":", 1)[1]
        out[target] = spec
    return out


def _env_by_name(service: dict) -> dict[str, str]:
    out: dict[str, str] = {}
    for item in service.get("environment", []):
        name, _, value = str(item).partition("=")
        out[name] = value
    return out


def test_django_mounts_both_databases(services: dict) -> None:
    # Arrange — the control for every parity assertion in this file.
    targets = _mounts_by_target(services["django"])
    # Act
    present = [t for t in LOCAL_DB_TARGETS if t in targets]
    # Assert
    assert present == list(LOCAL_DB_TARGETS), sorted(targets)


@pytest.mark.parametrize("target", LOCAL_DB_TARGETS)
def test_worker_mounts_the_same_database_source(services: dict, target: str) -> None:
    # Arrange
    django_spec = _mounts_by_target(services["django"]).get(target)
    worker_spec = _mounts_by_target(services["celery_worker"]).get(target)
    # Act
    identical = worker_spec == django_spec
    # Assert
    assert identical, (
        f"celery_worker must mount {target} exactly as django does — the public "
        f"/status/ verdicts are computed in the worker.\n"
        f"  django:        {django_spec}\n  celery_worker: {worker_spec}"
    )


def test_worker_sets_the_same_local_db_env(services: dict) -> None:
    # Arrange
    django_env = _env_by_name(services["django"])
    worker_env = _env_by_name(services["celery_worker"])
    # Act
    mismatched = {
        name: (django_env.get(name), worker_env.get(name))
        for name in LOCAL_DB_ENV
        if django_env.get(name) != worker_env.get(name)
    }
    # Assert
    assert not mismatched, (
        "celery_worker's local-database environment differs from django's "
        f"(name: (django, worker)): {mismatched}"
    )


def test_the_control_django_sets_all_four_variables(services: dict) -> None:
    # Arrange — without this, an env that is absent on BOTH sides passes parity.
    django_env = _env_by_name(services["django"])
    # Act
    missing = [name for name in LOCAL_DB_ENV if not django_env.get(name)]
    # Assert
    assert missing == [], missing
