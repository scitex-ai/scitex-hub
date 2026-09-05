#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/scitex_hub/_dev_preview/test__classify.py

"""Changed paths map to the SMALLEST follow-up the preview needs.

The dev stack reacts to most edits by itself (runserver autoreload, template
watcher, CSS from the bind mount); a blanket reload on every merge would
recreate the container every few minutes and a blanket rebuild would cost
10-25 min per merge. These tests pin the rules in
:mod:`scitex_hub._dev_preview._classify`:

* one parametrized case per rule — every REBUILD / RELOAD / MIGRATE /
  NPM_BUILD trigger listed in the module docstring, plus the ``.py`` /
  ``.html`` / ``.css`` / ``.md`` paths that must stay a no-op — including
  the two files a rule USED to catch for nothing: ``docs/sphinx/
  requirements.txt`` (Read the Docs only; a docs bump is not an image
  change) and anything under ``deployment/docker/envs/`` (the loaded
  ``.env.dev`` is untracked; the tracked example / README change nothing);
* precedence — REBUILD supersedes RELOAD, orthogonal actions combine in the
  fixed order ``(rebuild | reload), migrate, npm_build``;
* edge cases — an empty diff is a no-op, a leading ``./`` is tolerated, a
  non-``.py`` file under ``migrations/`` and a ``migrations.py`` outside
  such a directory do not trigger a migrate.

Pure functions in, pure data out; nothing here touches git or docker.
"""

from __future__ import annotations

import pytest

from scitex_hub._dev_preview import Plan, classify

DOCKER_DEV = "deployment/docker/docker_dev"

SINGLE_PATH_CASES = [
    # REBUILD — exactly what the dev Dockerfile copies before installing
    (f"{DOCKER_DEV}/Dockerfile", ("rebuild",)),
    (f"{DOCKER_DEV}/install_ecosystem.sh", ("rebuild",)),
    ("pyproject.toml", ("rebuild",)),
    # REBUILD + NPM_BUILD — node deps change the image AND the bundle
    ("package.json", ("rebuild", "npm_build")),
    ("package-lock.json", ("rebuild", "npm_build")),
    # RELOAD — runtime contract changes, image does not
    (f"{DOCKER_DEV}/docker-compose.yml", ("reload",)),
    (f"{DOCKER_DEV}/docker-compose.override.yml", ("reload",)),
    (f"{DOCKER_DEV}/docker-compose.preview.yml", ("reload",)),
    (f"{DOCKER_DEV}/entrypoint.sh", ("reload",)),
    (f"{DOCKER_DEV}/server.sh", ("reload",)),
    (f"{DOCKER_DEV}/start-with-reload.sh", ("reload",)),
    (f"{DOCKER_DEV}/run_daphne_with_autoreload.py", ("reload",)),
    (f"{DOCKER_DEV}/watch_templates.sh", ("reload",)),
    # MIGRATE — the entrypoint skips migrate on every restart after the first
    ("apps/project_app/migrations/0042_add_field.py", ("migrate",)),
    ("migrations/0001_initial.py", ("migrate",)),
    # NPM_BUILD — the bundle behind the tunnel is pre-built
    ("static/ts/app.ts", ("npm_build",)),
    ("apps/x/static/x/ts/widget.tsx", ("npm_build",)),
    ("static/ts/ウィジェット.ts", ("npm_build",)),
    ("vite.config.ts", ("npm_build",)),
    ("vite.config.devapp.ts", ("npm_build",)),
    ("tsconfig.json", ("npm_build",)),
    ("tsconfig/tsconfig.app.json", ("npm_build",)),
    # NOOP — autoreload / template watcher / bind mount handle these
    ("apps/project_app/views.py", ()),
    ("templates/base.html", ()),
    ("static/css/main.css", ()),
    ("README.md", ()),
    ("static/js/legacy.js", ()),
    ("apps/x/migrations/README.md", ()),
    ("apps/x/migrations.py", ()),
    # NOOP — the dev Dockerfile reads no requirements file; hub's only tracked
    # one feeds Read the Docs, and a docs bump used to cost a 10-25 min rebuild
    ("docs/sphinx/requirements.txt", ()),
    ("requirements.txt", ()),
    # NOOP — the stack loads the UNTRACKED .env.dev; the tracked example and
    # README change nothing at runtime, and a recreate drops live sessions
    ("deployment/docker/envs/.env.example", ()),
    ("deployment/docker/envs/README.md", ()),
]


@pytest.mark.parametrize("path,expected", SINGLE_PATH_CASES)
def test_single_path_maps_to_its_follow_up(path: str, expected: tuple[str, ...]):
    """Each rule in the classifier docstring fires for its path and only its path."""
    # Arrange
    paths = [path]
    # Act
    plan = classify(paths)
    # Assert
    assert plan.actions() == expected


def test_rebuild_supersedes_reload():
    """A rebuild recreates the container as part of the swap; a reload on top is waste."""
    # Arrange
    paths = [f"{DOCKER_DEV}/docker-compose.yml", f"{DOCKER_DEV}/Dockerfile"]
    # Act
    plan = classify(paths)
    # Assert
    assert plan.actions() == ("rebuild",)


def test_orthogonal_actions_combine_in_fixed_order():
    """Container first, then schema, then bundle — the order the engine executes."""
    # Arrange
    paths = [
        "static/ts/app.ts",
        "apps/x/migrations/0002_more.py",
        f"{DOCKER_DEV}/entrypoint.sh",
    ]
    # Act
    plan = classify(paths)
    # Assert
    assert plan.actions() == ("reload", "migrate", "npm_build")


def test_empty_diff_is_a_noop():
    """No changed paths means nothing to do."""
    # Arrange
    paths: list[str] = []
    # Act
    plan = classify(paths)
    # Assert
    assert plan.is_noop is True


def test_noop_plan_reports_is_noop_for_autoreload_only_changes():
    """A Python-only merge is live by autoreload and must not touch the container."""
    # Arrange
    paths = ["apps/x/views.py", "templates/x.html", "static/css/x.css"]
    # Act
    plan = classify(paths)
    # Assert
    assert (plan.is_noop, plan) == (True, Plan())


def test_leading_dot_slash_is_tolerated():
    """A ``./``-prefixed path (hand-typed or tool-emitted) classifies like the bare one."""
    # Arrange
    paths = [f"./{DOCKER_DEV}/Dockerfile"]
    # Act
    plan = classify(paths)
    # Assert
    assert plan.rebuild is True


def test_plan_is_frozen_pure_data():
    """The plan is a value: the engine may not mutate it mid-run."""
    # Arrange
    plan = classify(["pyproject.toml"])

    # Act
    def mutate() -> None:
        plan.rebuild = False  # type: ignore[misc]

    # Assert
    with pytest.raises(AttributeError):
        mutate()


# EOF
