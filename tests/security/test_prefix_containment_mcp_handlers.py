#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sibling-prefix path escape in the project MCP file handlers.

FINDING (2026-07-22)
    ``src/scitex_hub/project/_mcp/handlers.py::_resolve_safe`` — the single
    chokepoint every MCP file/exec handler goes through — guarded BOTH of its
    boundaries with a STRING PREFIX::

        root    = Path(root_path).resolve()
        allowed = Path(ALLOWED_DATA_ROOT).resolve()

        if not str(root).startswith(str(allowed)):        # site 1
            raise ValueError(...)
        target = (root / relative_path).resolve()
        if not str(target).startswith(str(root)):         # site 2
            raise ValueError(...)

    ``str.startswith`` is not path containment. A sibling directory whose name
    merely EXTENDS the root satisfies it:

    site 1  ALLOWED_DATA_ROOT ``/data/users`` admitted a root_path of
            ``/data/users-evil/proj`` — an arbitrary directory OUTSIDE the
            configured data root, from which every handler (read, write,
            search, exec_python, exec_shell) then operated freely.
    site 2  project root ``/data/users/alice/proj`` admitted
            ``/data/users/alice/proj-other/secret.txt``, reached with the
            relative path ``../proj-other/secret.txt`` — the exact traversal
            the module docstring claims is "blocked at resolution time".

FIX
    ``_is_within()`` — component-wise containment via
    ``Path.resolve().relative_to()``, the same shape as
    ``validate_path_in_project()`` in the Django tree. The helper is local to
    the package: ``src/scitex_hub/`` must not import ``apps.infra.*``, which
    would invert the dependency direction.

DESIGN NOTES
- The data root is steered through the REAL configuration channel: handlers.py
  reads ``SCITEX_PROJECT_DATA_ROOT`` from the environment at import time, so
  each fixture sets that variable and imports a fresh module. No production
  attribute is rewritten.
- The module is loaded BY FILE PATH from this checkout. ``scitex_hub`` is
  installed editable and may resolve to a *different* working tree on sys.path;
  anchoring on ``__file__`` guarantees the exploit runs against the source that
  ships with these tests, in any checkout or worktree.
- Everything runs on a real ``tmp_path`` filesystem, so the escape is a real
  read of a real neighbouring file — not a mock of one.
- No database and no Django settings are touched.
"""

import asyncio
import importlib.util
import os
from pathlib import Path

import pytest

pytestmark = pytest.mark.security

DATA_ROOT_ENV = "SCITEX_PROJECT_DATA_ROOT"

_HANDLERS_PATH = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "scitex_hub"
    / "project"
    / "_mcp"
    / "handlers.py"
)

SECRET = "neighbour-project-data-must-not-leak\n"
OWN = "my own project notes\n"


def _load_handlers():
    """Import handlers.py from THIS checkout, bypassing any editable install."""
    spec = importlib.util.spec_from_file_location(
        "_scitex_hub_mcp_handlers_under_test", _HANDLERS_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def handlers_rooted_at():
    """Factory: configure the real data-root env var, then import handlers.py."""
    original = os.environ.get(DATA_ROOT_ENV)

    def _load(data_root):
        os.environ[DATA_ROOT_ENV] = str(data_root)
        return _load_handlers()

    yield _load

    if original is None:
        os.environ.pop(DATA_ROOT_ENV, None)
    else:
        os.environ[DATA_ROOT_ENV] = original


def _project_tree(tmp_path):
    """users/alice/proj (legit) beside users/alice/proj-other (the neighbour)."""
    users = tmp_path / "users"
    proj = users / "alice" / "proj"
    proj.mkdir(parents=True)
    (proj / "notes.txt").write_text(OWN)

    # Name EXTENDS "proj" — this is what defeats a startswith() guard.
    sibling = users / "alice" / "proj-other"
    sibling.mkdir(parents=True)
    (sibling / "secret.txt").write_text(SECRET)
    return users, proj


# ---------------------------------------------------------------- site 2 ----


@pytest.fixture
def sibling_project_read(tmp_path, handlers_rooted_at):
    """Read a file in the neighbouring project via ``../proj-other/``."""
    users, proj = _project_tree(tmp_path)
    handlers = handlers_rooted_at(users)

    return asyncio.run(
        handlers.read_file_handler(
            root_path=str(proj), relative_path="../proj-other/secret.txt"
        )
    )


def test_sibling_project_read_is_rejected(sibling_project_read):
    # Arrange
    result = sibling_project_read
    # Act
    succeeded = result.get("success")
    # Assert
    assert succeeded is False, result


def test_sibling_project_secret_is_not_returned(sibling_project_read):
    # Arrange
    result = sibling_project_read
    # Act
    body = result.get("content", "")
    # Assert
    assert SECRET.strip() not in body, result


@pytest.fixture
def sibling_project_listing(tmp_path, handlers_rooted_at):
    """The same escape through the directory-listing handler.

    An escaping path that gets PAST the guard also blows up further down
    (``list_files_handler`` then calls ``target.relative_to(root)``, which
    raises for an out-of-root target). That crash is not a rejection either,
    so it is recorded as a non-False ``success`` rather than allowed to abort
    the fixture — the gate must read as a failed assertion, not an error.
    """
    users, proj = _project_tree(tmp_path)
    handlers = handlers_rooted_at(users)

    try:
        return asyncio.run(
            handlers.list_files_handler(
                root_path=str(proj), relative_path="../proj-other"
            )
        )
    except Exception as exc:  # noqa: BLE001 — any escape past the guard counts
        return {"success": f"escaped the guard, then raised {exc!r}"}


def test_sibling_project_listing_is_rejected(sibling_project_listing):
    # Arrange
    result = sibling_project_listing
    # Act
    succeeded = result.get("success")
    # Assert
    assert succeeded is False, result


# ---------------------------------------------------------------- site 1 ----


@pytest.fixture
def root_outside_data_root(tmp_path, handlers_rooted_at):
    """root_path sits in a sibling of the data root whose name extends it."""
    users = tmp_path / "users"
    users.mkdir()

    # "users-evil" starts with "users" — outside the data root, yet a
    # startswith() guard waves it through.
    outside = tmp_path / "users-evil" / "proj"
    outside.mkdir(parents=True)
    (outside / "secret.txt").write_text(SECRET)

    handlers = handlers_rooted_at(users)

    return asyncio.run(
        handlers.read_file_handler(root_path=str(outside), relative_path="secret.txt")
    )


def test_root_outside_data_root_is_rejected(root_outside_data_root):
    # Arrange
    result = root_outside_data_root
    # Act
    succeeded = result.get("success")
    # Assert
    assert succeeded is False, result


def test_root_outside_data_root_leaks_no_content(root_outside_data_root):
    # Arrange
    result = root_outside_data_root
    # Act
    body = result.get("content", "")
    # Assert
    assert SECRET.strip() not in body, result


# -------------------------------------------------------- anti-regression ----


@pytest.fixture
def legitimate_read(tmp_path, handlers_rooted_at):
    """A plain in-root read must still work — 'reject everything' is not a fix."""
    users, proj = _project_tree(tmp_path)
    handlers = handlers_rooted_at(users)

    return asyncio.run(
        handlers.read_file_handler(root_path=str(proj), relative_path="notes.txt")
    )


def test_in_root_file_still_reads(legitimate_read):
    # Arrange
    result = legitimate_read
    # Act
    succeeded = result.get("success")
    # Assert
    assert succeeded is True, result


def test_in_root_file_returns_its_content(legitimate_read):
    # Arrange
    result = legitimate_read
    # Act
    body = result.get("content", "")
    # Assert
    assert body == OWN, result


@pytest.fixture
def legitimate_listing(tmp_path, handlers_rooted_at):
    """The project's own directory listing must still work."""
    users, proj = _project_tree(tmp_path)
    handlers = handlers_rooted_at(users)

    return asyncio.run(
        handlers.list_files_handler(root_path=str(proj), relative_path=".")
    )


def test_in_root_listing_still_succeeds(legitimate_listing):
    # Arrange
    result = legitimate_listing
    # Act
    succeeded = result.get("success")
    # Assert
    assert succeeded is True, result


def test_in_root_listing_sees_own_file(legitimate_listing):
    # Arrange
    result = legitimate_listing
    # Act
    names = sorted(e["name"] for e in result.get("tree", []))
    # Assert
    assert names == ["notes.txt"], result


@pytest.fixture
def nested_subdirectory_read(tmp_path, handlers_rooted_at):
    """A deeper in-root path must still resolve (containment, not equality)."""
    users, proj = _project_tree(tmp_path)
    nested = proj / "sub" / "deeper"
    nested.mkdir(parents=True)
    (nested / "inner.txt").write_text(OWN)
    handlers = handlers_rooted_at(users)

    return asyncio.run(
        handlers.read_file_handler(
            root_path=str(proj), relative_path="sub/deeper/inner.txt"
        )
    )


def test_nested_in_root_file_still_reads(nested_subdirectory_read):
    # Arrange
    result = nested_subdirectory_read
    # Act
    succeeded = result.get("success")
    # Assert
    assert succeeded is True, result

# EOF
