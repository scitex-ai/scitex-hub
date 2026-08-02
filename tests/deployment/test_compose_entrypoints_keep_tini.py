#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Every compose `entrypoint:` override must keep tini as PID 1.

WHY THIS TEST EXISTS. ``Dockerfile.prod`` installs tini as the image
ENTRYPOINT specifically so PID 1 reaps orphaned children. But a compose
``entrypoint:`` override REPLACES the image ENTRYPOINT **wholesale** — it does
not prepend — so every service that overrides it silently loses its reaper.
Nothing warns. The container starts, serves traffic, and looks healthy while
``<defunct>`` children accumulate underneath it.

That is not hypothetical. Issue #148 counted 95 zombies in prod, leaking since
2026-04-15, from the terminal path (``pty.fork()`` + ``execvpe("srun", ...)``)
under a daphne PID 1 with no SIGCHLD handler. It was fixed on ``main`` in
67a02ef0f via ``init: true`` — and that commit was never merged back to
``develop``, so the fix silently reverted for everything built from develop.

Measured on the running host 2026-08-03, which is what this test encodes:
    prod-django            PID 1 = daphne   <- unprotected
    prod-celery_worker     PID 1 = tini
    staging-django         PID 1 = daphne   <- unprotected
    staging-celery_worker  PID 1 = celery   <- unprotected
    staging-celery_beat    PID 1 = celery   <- unprotected
Four live containers, three of them in a file nobody had looked at, because the
original fix and the original report both named only django.

A COMMENT WOULD NOT HAVE HELD THIS. The convention was already written down, in
docker_prod/docker-compose.yml above celery_worker, in prose that explains the
exact failure mode — and django in that same file still had the bug, as did all
of staging. A rule that must be remembered is forgotten precisely when it
matters, so this is a gate instead.
"""

from pathlib import Path

import pytest
import yaml

_REPO_ROOT = Path(__file__).resolve().parents[2]

# The compose files that produce RUNNING containers, verified against
# `docker inspect ... com.docker.compose.project.config_files` on the host
# 2026-08-03. Deliberately NOT a glob over deployment/docker/*.yml: that tree
# also holds files nothing launches (docker-compose.prod.yml among them), and
# gating on dead files trains people to edit a test to make CI green.
_LIVE_COMPOSE_FILES = (
    "deployment/docker/docker_prod/docker-compose.yml",
    "deployment/docker/docker-compose.staging.yml",
)

_TINI = "/usr/bin/tini"


def _overrides(rel_path):
    """(service, entrypoint) for every service overriding entrypoint."""
    doc = yaml.safe_load((_REPO_ROOT / rel_path).read_text())
    found = []
    for name, svc in (doc.get("services") or {}).items():
        if isinstance(svc, dict) and svc.get("entrypoint") is not None:
            found.append((name, svc["entrypoint"]))
    return found


_ALL = [
    (path, service, entrypoint)
    for path in _LIVE_COMPOSE_FILES
    for service, entrypoint in _overrides(path)
]


def test_every_live_compose_file_exists():
    # Arrange — a missing file would make the whole sweep silently vacuous,
    # so its presence is checked as its own contract.
    paths = [(p, (_REPO_ROOT / p).is_file()) for p in _LIVE_COMPOSE_FILES]
    # Act
    missing = [p for p, exists in paths if not exists]
    # Assert
    assert missing == []


def test_sweep_actually_found_entrypoint_overrides():
    # Arrange — THE POSITIVE CONTROL, and the reason it is its own test:
    # without it the parametrised assertion below passes with ZERO cases the
    # moment these files are renamed, restructured, or the key is spelled
    # differently. A green suite would then mean "found nothing", which is
    # indistinguishable from "everything is correct".
    cases = _ALL
    # Act
    count = len(cases)
    # Assert
    assert count > 0


def test_every_live_compose_file_contributes_at_least_one_case():
    # Arrange — per-file control. One file supplying every case would let
    # another drop out of the sweep unnoticed: the same vacuity, one level down.
    expected = set(_LIVE_COMPOSE_FILES)
    # Act
    covered = {path for path, _, _ in _ALL}
    # Assert
    assert covered == expected


@pytest.mark.parametrize(
    "path,service,entrypoint",
    _ALL,
    ids=[f"{Path(p).name}::{s}" for p, s, _ in _ALL],
)
def test_entrypoint_override_keeps_tini_as_pid1(path, service, entrypoint):
    # Arrange
    # compose accepts a string or a list; normalise to tokens.
    tokens = entrypoint.split() if isinstance(entrypoint, str) else list(entrypoint)
    # Act
    # tini must be the FIRST token: anywhere else it is not PID 1, and PID 1
    # is the only position from which it can reap.
    first = tokens[:1]
    # Assert
    assert first == [_TINI], (
        f"{path} service '{service}' overrides entrypoint without tini first "
        f"({tokens!r}). The override replaces the image ENTRYPOINT wholesale, "
        f"so this container will run with no reaper and accumulate zombies "
        f"(issue #148). Use: [\"{_TINI}\", \"--\", ...existing...]."
    )
