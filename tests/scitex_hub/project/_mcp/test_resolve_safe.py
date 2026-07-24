#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Path-containment tests for the MCP project handler ``_resolve_safe``.

Security class: a *string prefix* is not *containment*. The old guard used
``str(target).startswith(str(root))``, so a sibling directory that merely
shares a string prefix (``/data/users`` vs ``/data/users-evil``) slipped
through. ``_resolve_safe`` gates every MCP file handler below it, including
``exec_python_handler`` / ``exec_shell_handler`` (create_subprocess_exec),
so a prefix escape is an arbitrary-path (and arbitrary-exec) primitive.

These tests are Django-free by design: ``scitex_hub`` must not import
``apps.infra.*``. They drive ``_resolve_safe`` directly with REAL on-disk
directories under ``tmp_path``.

Each escaping case asserts ``pytest.raises(ValueError)``: on the OLD
prefix-match code the call returns a path instead of raising, so the test
FAILS on old code and PASSES on the patched code (a genuine red/green proof,
not a tautology).

``ALLOWED_DATA_ROOT`` is a module global read inside ``_resolve_safe``. We
do NOT use the forbidden ``monkeypatch`` fixture; instead a hand-rolled
yield fixture saves the real attribute, points it at a tmp directory, and
restores it on teardown.
"""

import pytest

from scitex_hub.project._mcp import handlers


@pytest.fixture
def allowed_root(tmp_path):
    """Point the handler's ALLOWED_DATA_ROOT at a real tmp dir; restore after.

    Hand-rolled save/restore (not monkeypatch) so teardown is explicit and
    production is exercised with a real filesystem root.
    """
    original = handlers.ALLOWED_DATA_ROOT
    root = tmp_path / "data" / "users"
    root.mkdir(parents=True)
    handlers.ALLOWED_DATA_ROOT = str(root)
    try:
        yield root
    finally:
        handlers.ALLOWED_DATA_ROOT = original


def test_root_sibling_prefix_of_allowed_root_is_rejected(allowed_root):
    """A root that is a string-prefix SIBLING of ALLOWED_DATA_ROOT must be
    rejected. ``/data/users`` must NOT admit ``/data/users-evil`` -- the exact
    case the old ``startswith`` guard let through.
    """
    # Arrange
    evil_sibling = allowed_root.parent / "users-evil"
    evil_sibling.mkdir(parents=True)
    # Act / Assert: resolving a sibling-prefix root must raise, not return.
    # Assert
    with pytest.raises(ValueError):
        handlers._resolve_safe(str(evil_sibling))


def test_relative_path_escaping_root_is_rejected(allowed_root):
    """A relative_path escaping into a sibling-prefix project must be
    rejected. root ``.../proj`` must NOT admit ``../proj-other/secret``.
    """
    # Arrange
    root = allowed_root / "proj"
    sibling = allowed_root / "proj-other"
    root.mkdir(parents=True)
    sibling.mkdir(parents=True)
    (sibling / "secret.txt").write_text("TENANT-B-SENTINEL")
    # Act
    # Assert
    with pytest.raises(ValueError):
        handlers._resolve_safe(str(root), "../proj-other/secret.txt")


def test_dotdot_traversal_is_rejected(allowed_root):
    """Plain ``..`` traversal above the root is rejected."""
    # Arrange
    root = allowed_root / "proj"
    root.mkdir(parents=True)
    # Act
    # Assert
    with pytest.raises(ValueError):
        handlers._resolve_safe(str(root), "../../../../etc/passwd")


def test_legitimate_nested_path_is_allowed(allowed_root):
    """A genuine in-root nested path resolves without error (proves the fix
    is real containment, not a blanket deny)."""
    # Arrange
    root = allowed_root / "proj"
    root.mkdir(parents=True)
    # Act
    resolved = handlers._resolve_safe(str(root), "a/b/c.txt")
    # Assert
    assert resolved == (root / "a" / "b" / "c.txt").resolve()


def test_root_itself_is_allowed(allowed_root):
    """Resolving the root with no relative path succeeds."""
    # Arrange
    root = allowed_root / "proj"
    root.mkdir(parents=True)
    # Act
    resolved = handlers._resolve_safe(str(root))
    # Assert
    assert resolved == root.resolve()


if __name__ == "__main__":
    import os

    pytest.main([os.path.abspath(__file__), "-v"])
