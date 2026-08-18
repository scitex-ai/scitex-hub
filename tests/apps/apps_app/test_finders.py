#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for DevAppStaticFinder.

A MISS MUST BE ``[]``, NEVER ``None`` — and this file used to assert the
opposite, which is how the bug it now pins survived.

``django.contrib.staticfiles.finders.find()`` aggregates over every
configured finder and wraps a non-list answer as ``[answer]``. A ``None``
therefore becomes a truthy ``[None]`` and is returned as if it were a
match; ``staticfiles.views.serve`` then runs ``os.path.split([None])`` and
raises ``TypeError: expected str, bytes or os.PathLike object, not list``.
The result is HTTP 500 for every static file that exists nowhere, where
the right answer is 404. The two built-in finders return ``[]``, so this
finder is the only reason the project could hit it.

Measured 2026-08-17 in CI run 32056013931: with the screenshot job pointed
at Vite-built assets, EVERY ``/static/vite/*.js`` answered 500 with that
traceback. No JavaScript ran; the visitor heartbeat is one of those
entries, so it never fired; the pooled visitor's 120-second probation
lease was never promoted to the full hour, expired mid-capture, and four
pages were photographed as ``readonly_visitor``.

Real filesystem throughout (``tmp_path``, real directories, real files)
and ``override_settings`` to point BASE_DIR at them — no mocks.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from django.contrib.staticfiles import finders as django_finders
from django.test import override_settings

from apps.workspace.apps_app.finders import DevAppStaticFinder

ASSET = "pomodoro_app/css/pomodoro_app.css"


@pytest.fixture
def finder():
    return DevAppStaticFinder()


@pytest.fixture
def empty_base(tmp_path):
    """A real BASE_DIR with no ``data/users`` under it."""
    return tmp_path / "no-users-here"


@pytest.fixture
def base_with_dev_app(tmp_path):
    """A real BASE_DIR holding a real dev-app static file."""
    static_dir = tmp_path / "data" / "users" / "alice" / "proj" / "pom" / "static"
    (static_dir / "pomodoro_app" / "css").mkdir(parents=True)
    (static_dir / ASSET).write_text("body{}", encoding="utf-8")
    return tmp_path


def test_find_returns_empty_list_when_no_users_dir(finder, empty_base):
    # Arrange
    expected = []

    # Act
    with override_settings(BASE_DIR=empty_base):
        result = finder.find(ASSET)

    # Assert
    assert result == expected


def test_find_all_returns_empty_list_when_no_users_dir(finder, empty_base):
    # Arrange
    expected = []

    # Act
    with override_settings(BASE_DIR=empty_base):
        result = finder.find(ASSET, all=True)

    # Assert
    assert result == expected


def test_find_returns_empty_list_for_nonexistent_file(finder, base_with_dev_app):
    # Arrange
    missing = "nonexistent_app/does_not_exist.css"

    # Act
    with override_settings(BASE_DIR=base_with_dev_app):
        result = finder.find(missing)

    # Assert
    assert result == []


def test_find_all_returns_empty_list_for_nonexistent_file(finder, base_with_dev_app):
    # Arrange
    missing = "nonexistent_app/does_not_exist.css"

    # Act
    with override_settings(BASE_DIR=base_with_dev_app):
        result = finder.find(missing, all=True)

    # Assert
    assert result == []


def test_find_returns_the_path_of_a_real_dev_app_asset(finder, base_with_dev_app):
    # Arrange
    expected = base_with_dev_app / "data" / "users" / "alice" / "proj" / "pom"

    # Act
    with override_settings(BASE_DIR=base_with_dev_app):
        result = finder.find(ASSET)

    # Assert
    assert result == str(expected / "static" / ASSET)


def test_found_path_is_a_real_readable_file(finder, base_with_dev_app):
    # Arrange
    expected_body = "body{}"

    # Act
    with override_settings(BASE_DIR=base_with_dev_app):
        result = finder.find(ASSET)

    # Assert
    assert Path(result).read_text(encoding="utf-8") == expected_body


def test_find_all_returns_the_match_in_a_list(finder, base_with_dev_app):
    # Arrange
    expected = base_with_dev_app / "data" / "users" / "alice" / "proj" / "pom"

    # Act
    with override_settings(BASE_DIR=base_with_dev_app):
        result = finder.find(ASSET, all=True)

    # Assert
    assert result == [str(expected / "static" / ASSET)]


def test_list_yields_nothing_when_no_users_dir(finder, empty_base):
    # Arrange
    expected = []

    # Act
    with override_settings(BASE_DIR=empty_base):
        items = list(finder.list([]))

    # Assert
    assert items == expected


def test_list_yields_the_relative_path_of_a_real_asset(finder, base_with_dev_app):
    # Arrange
    expected = ASSET

    # Act
    with override_settings(BASE_DIR=base_with_dev_app):
        names = [name for name, _storage in finder.list([])]

    # Assert
    assert names == [expected]


def test_find_survives_an_unreadable_base_dir(finder):
    """An unreadable BASE_DIR means "no dev-app assets", not a crash.

    ``Path.is_dir()`` raises ``PermissionError`` when a parent is
    unreadable — real for an unprivileged process pointed at ``/root``.
    The finder runs on EVERY static lookup, so it must answer rather than
    take the request down with it.
    """
    # Arrange
    unreadable = Path("/root")

    # Act
    with override_settings(BASE_DIR=unreadable):
        result = finder.find("anything.css")

    # Assert
    assert result == []


def test_aggregated_find_returns_none_for_a_file_that_exists_nowhere():
    """THE REGRESSION THIS FILE EXISTS FOR — the real aggregator.

    Not the finder in isolation: ``django.contrib.staticfiles.finders``
    ``find()``, the function ``staticfiles.views.serve`` actually calls,
    running over the project's REAL configured finder chain. With the old
    ``None`` return this answered ``[None]`` — truthy, list-shaped, and
    fatal one frame later in ``os.path.split``. Anything other than
    ``None`` here is a 500 waiting for the next missing asset.
    """
    # Arrange
    nowhere = "definitely/not/a/real/asset-3f9c1a.js"

    # Act
    result = django_finders.find(nowhere)

    # Assert
    assert result is None


# EOF
