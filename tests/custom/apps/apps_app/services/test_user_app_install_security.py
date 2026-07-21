#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""F0+F1 negative-case security tests — directory-traversal + injection blocked.

Proves the input validators in
:mod:`apps.workspace.apps_app.services._user_app_install` reject every
malicious ``module_name`` / ``owner`` / ``repo`` / ``commit`` shape
BEFORE any filesystem touch or subprocess invocation, per the M4 done-
gate (lead msg 37b38d69 + a2b21da8). No mocks — direct exercise of the
production functions with real ValueError / Path semantics.

Companion to the positive integration test in
``test_user_app_install_e2e.py`` (real pip install from a local
fixture). Together these two files are the M4 proof gate.
"""

from __future__ import annotations

import pytest

from apps.workspace.apps_app.services._user_app_install import (
    _safe_commit,
    _safe_identifier,
)

# ---------------------------------------------------------------------------
# _safe_identifier — rejects every traversal / injection shape
# ---------------------------------------------------------------------------


class TestSafeIdentifierRejectsTraversal:
    """Module-name validator blocks ``..`` and any path-escape shape."""

    def test_rejects_dot_dot_segment(self) -> None:
        # Arrange
        bad = ".."
        raised: Exception | None = None
        # Act
        try:
            _safe_identifier(bad, "module_name")
        except ValueError as exc:
            raised = exc
        # Assert
        assert raised is not None and "unsafe value for module_name" in str(raised)

    def test_rejects_parent_dir_prefix(self) -> None:
        # Arrange
        bad = "../evil"
        raised: Exception | None = None
        # Act
        try:
            _safe_identifier(bad, "module_name")
        except ValueError as exc:
            raised = exc
        # Assert
        assert raised is not None

    def test_rejects_forward_slash(self) -> None:
        # Arrange
        bad = "a/b"
        raised: Exception | None = None
        # Act
        try:
            _safe_identifier(bad, "module_name")
        except ValueError as exc:
            raised = exc
        # Assert
        assert raised is not None

    def test_rejects_backslash_in_module_name(self) -> None:
        # Arrange
        bad = "a\\b"
        raised: Exception | None = None
        # Act
        try:
            _safe_identifier(bad, "module_name")
        except ValueError as exc:
            raised = exc
        # Assert
        assert raised is not None


class TestSafeIdentifierRejectsShellMetachars:
    """Module-name validator blocks shell-injection shapes."""

    def test_rejects_semicolon_rm(self) -> None:
        # Arrange
        bad = "a;rm -rf /"
        raised: Exception | None = None
        # Act
        try:
            _safe_identifier(bad, "module_name")
        except ValueError as exc:
            raised = exc
        # Assert
        assert raised is not None and "unsafe value for module_name" in str(raised)

    def test_rejects_pipe_to_shell(self) -> None:
        # Arrange
        bad = "a|sh"
        raised: Exception | None = None
        # Act
        try:
            _safe_identifier(bad, "module_name")
        except ValueError as exc:
            raised = exc
        # Assert
        assert raised is not None

    def test_rejects_backtick_command_substitution(self) -> None:
        # Arrange
        bad = "a`whoami`"
        raised: Exception | None = None
        # Act
        try:
            _safe_identifier(bad, "module_name")
        except ValueError as exc:
            raised = exc
        # Assert
        assert raised is not None

    def test_rejects_newline_log_injection(self) -> None:
        # Arrange — control char in identifier would inject a fake log line.
        bad = "a\nFAKE LOG ENTRY"
        raised: Exception | None = None
        # Act
        try:
            _safe_identifier(bad, "module_name")
        except ValueError as exc:
            raised = exc
        # Assert
        assert raised is not None


class TestSafeIdentifierAcceptsValidShapes:
    """Module-name validator passes legitimate identifiers."""

    def test_accepts_simple_name(self) -> None:
        # Arrange
        good = "my_app"
        # Act
        returned = _safe_identifier(good, "module_name")
        # Assert
        assert returned == good

    def test_accepts_canonical_user_app_with_underscore_suffix(self) -> None:
        # Arrange
        good = "scitex_live_paper_hub_app"
        # Act
        returned = _safe_identifier(good, "module_name")
        # Assert
        assert returned == good

    def test_accepts_hyphen_in_repo_slug(self) -> None:
        # Arrange — gitea repo slugs commonly use hyphens.
        good = "my-repo-name"
        # Act
        returned = _safe_identifier(good, "gitea_repo")
        # Assert
        assert returned == good


# ---------------------------------------------------------------------------
# _safe_commit — rejects every non-hex / wrong-length shape
# ---------------------------------------------------------------------------


class TestSafeCommitRejectsNonSha:
    """Commit validator blocks non-hex / wrong-length values."""

    def test_rejects_non_hex_char(self) -> None:
        # Arrange — 'g' is not a hex digit.
        bad = "g" * 40
        raised: Exception | None = None
        # Act
        try:
            _safe_commit(bad)
        except ValueError as exc:
            raised = exc
        # Assert
        assert raised is not None and "unsafe value for commit" in str(raised)

    def test_rejects_too_short(self) -> None:
        # Arrange — 6 hex chars is below the 7-min boundary.
        bad = "abcdef"
        raised: Exception | None = None
        # Act
        try:
            _safe_commit(bad)
        except ValueError as exc:
            raised = exc
        # Assert
        assert raised is not None

    def test_rejects_empty_string_commit(self) -> None:
        # Arrange
        bad = ""
        raised: Exception | None = None
        # Act
        try:
            _safe_commit(bad)
        except ValueError as exc:
            raised = exc
        # Assert
        assert raised is not None

    def test_rejects_path_traversal_attempt(self) -> None:
        # Arrange — even if length matches, '/' fails.
        bad = "abc/def" + "0" * 33
        raised: Exception | None = None
        # Act
        try:
            _safe_commit(bad)
        except ValueError as exc:
            raised = exc
        # Assert
        assert raised is not None


class TestSafeCommitAcceptsRealShas:
    """Commit validator accepts canonical Git SHAs."""

    def test_accepts_short_sha_7_chars(self) -> None:
        # Arrange
        good = "a1b2c3d"
        # Act
        returned = _safe_commit(good)
        # Assert
        assert returned == good

    def test_accepts_full_sha_40_chars(self) -> None:
        # Arrange
        good = "0123456789abcdef0123456789abcdef01234567"  # pragma: allowlist secret
        # Act
        returned = _safe_commit(good)
        # Assert
        assert returned == good


# EOF
