#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_hub/_dev_preview/_classify.py

"""Turn ``git diff --name-only`` into the follow-up the preview needs.

WHY A CLASSIFIER AND NOT "ALWAYS RELOAD"
----------------------------------------
The dev stack already reacts to most edits by itself: ``runserver``
autoreload restarts Django on ``.py`` changes, django-browser-reload picks
up templates, CSS is served straight from the bind mount. A blanket
``make ENV=dev reload`` on every merge would recreate the container every
few minutes for nothing and drop every live terminal / SSH-gateway session
in it. A blanket ``rebuild`` would take 10-25 min per merge. So each tick
runs the SMALLEST action that makes the merged change actually visible.

THE RULES (paths are repo-relative, as ``git diff --name-only`` prints them)
--------------------------------------------------------------------------
REBUILD (``make ENV=dev YES=1 rebuild``) — the image itself changes, i.e.
  exactly the inputs the dev Dockerfile copies before its install steps
  (``deployment/docker/docker_dev/Dockerfile``, read 2026-09-05: ``COPY
  pyproject.toml``, ``COPY package.json package-lock.json*``, plus the
  Dockerfile and ``install_ecosystem.sh`` themselves). NOT ``requirements*.txt``:
  hub's only tracked one is ``docs/sphinx/requirements.txt``, read by Read
  the Docs alone, and a basename glob on it cost a 10-25 min rebuild for a
  docs dependency bump.
RELOAD (``make ENV=dev reload`` = recreate the django service) — the
  container's runtime contract changes but the image does not:
  ``docker-compose.yml`` / ``docker-compose.override.yml`` /
  ``docker-compose.preview.yml`` under ``deployment/docker/docker_dev/``
  and the boot scripts there (``entrypoint.sh``, ``server.sh``,
  ``start-with-reload.sh``, ``run_daphne_with_autoreload.py``,
  ``watch_templates.sh``). NOT ``deployment/docker/envs/``: the file the
  stack loads (``.env.dev``) is untracked and never appears in a diff; the
  two tracked files there (``.env.example``, ``README.md``) change nothing
  at runtime, and a recreate drops every live session in the container.
MIGRATE (``docker exec <django> python manage.py migrate --noinput``) —
  any ``.py`` under a ``migrations/`` directory. This is a SEPARATE action,
  not a reload, because a recreate does NOT migrate: the dev entrypoint
  (``deployment/docker/docker_dev/entrypoint.sh``, read 2026-09-05) gates
  migrations on a sentinel that persists in the ``/app/logs`` volume::

      MIGRATION_SENTINEL="/app/logs/.migrations_done"
      ...
      if [ ! -f "$MIGRATION_SENTINEL" ]; then
          wait_for_database
          run_migrations
          ...
      else
          # Hot-reload restart - skip migrations
          echo_info "Hot-reload restart detected - skipping migrations"
          wait_for_database # Still wait for DB to be ready
      fi

  so every restart after the first one — and every rebuild, since the
  volume outlives the image — skips ``migrate``. autoreload loads the new
  migration MODULE, but the schema only changes when someone runs the
  command; a merged migration that nobody applies is exactly the kind of
  "preview says nothing" the operator asked us to end.
NPM_BUILD (``docker exec <django> npm run build``) — TypeScript is served
  from a pre-built bundle behind the tunnel, not from the Vite dev server:
  any ``.ts`` / ``.tsx``, ``vite.config*.ts``, ``tsconfig*.json``, and
  ``package.json`` / ``package-lock.json`` (which also REBUILD).

Precedence: REBUILD supersedes RELOAD (the rebuild recreates the container
anyway). MIGRATE and NPM_BUILD are orthogonal and run AFTER the container
is healthy. Everything else is a no-op.
"""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Iterable

__all__ = ["Plan", "classify"]

_DOCKER_DEV = "deployment/docker/docker_dev"

_REBUILD_EXACT = frozenset(
    {
        f"{_DOCKER_DEV}/Dockerfile",
        f"{_DOCKER_DEV}/install_ecosystem.sh",
        "pyproject.toml",
        "package.json",
        "package-lock.json",
    }
)

_RELOAD_EXACT = frozenset(
    {
        f"{_DOCKER_DEV}/docker-compose.yml",
        f"{_DOCKER_DEV}/docker-compose.override.yml",
        f"{_DOCKER_DEV}/docker-compose.preview.yml",
        f"{_DOCKER_DEV}/entrypoint.sh",
        f"{_DOCKER_DEV}/server.sh",
        f"{_DOCKER_DEV}/start-with-reload.sh",
        f"{_DOCKER_DEV}/run_daphne_with_autoreload.py",
        f"{_DOCKER_DEV}/watch_templates.sh",
    }
)

_NPM_SUFFIXES = frozenset({".ts", ".tsx"})
_NPM_BASENAME_GLOBS = ("vite.config*.ts", "tsconfig*.json")
_NPM_EXACT = frozenset({"package.json", "package-lock.json"})


@dataclass(frozen=True)
class Plan:
    """The follow-up a set of changed paths needs. Pure data."""

    rebuild: bool = False
    reload: bool = False
    migrate: bool = False
    npm_build: bool = False

    def actions(self) -> tuple[str, ...]:
        """Ordered action names: (rebuild | reload), migrate, npm_build.

        Rebuild supersedes reload — it recreates the container as part of
        the swap, so running both would recreate twice for nothing.
        """
        ordered: list[str] = []
        if self.rebuild:
            ordered.append("rebuild")
        elif self.reload:
            ordered.append("reload")
        if self.migrate:
            ordered.append("migrate")
        if self.npm_build:
            ordered.append("npm_build")
        return tuple(ordered)

    @property
    def is_noop(self) -> bool:
        """True when autoreload alone makes the change visible."""
        return not self.actions()


def _wants_rebuild(path: str) -> bool:
    return path in _REBUILD_EXACT


def _wants_reload(path: str) -> bool:
    return path in _RELOAD_EXACT


def _wants_migrate(parts: tuple[str, ...], suffix: str) -> bool:
    return suffix == ".py" and "migrations" in parts[:-1]


def _wants_npm_build(path: str, name: str, suffix: str) -> bool:
    return (
        suffix in _NPM_SUFFIXES
        or path in _NPM_EXACT
        or any(fnmatch.fnmatchcase(name, glob) for glob in _NPM_BASENAME_GLOBS)
    )


def classify(paths: Iterable[str]) -> Plan:
    """Classify repo-relative changed paths into a :class:`Plan`.

    Leading ``./`` is tolerated; Windows separators are not expected (git
    prints POSIX paths). An empty iterable is the no-op plan.
    """
    rebuild = reload = migrate = npm_build = False
    for raw in paths:
        path = raw.strip()
        if path.startswith("./"):
            path = path[2:]
        if not path:
            continue
        pure = PurePosixPath(path)
        name, suffix, parts = pure.name, pure.suffix, pure.parts
        rebuild = rebuild or _wants_rebuild(path)
        reload = reload or _wants_reload(path)
        migrate = migrate or _wants_migrate(parts, suffix)
        npm_build = npm_build or _wants_npm_build(path, name, suffix)
    return Plan(rebuild=rebuild, reload=reload, migrate=migrate, npm_build=npm_build)


# EOF
