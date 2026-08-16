"""Regression: git diff ``from``/``to`` refs must reject option injection.

apps/infra/project_app/views/repository/api/git_history.api_git_diff places
the ``from`` and ``to`` query params into a ``git diff`` argv in the ref
positions, which PRECEDE the ``--`` path separator. ``--`` therefore cannot
protect them: a value beginning with ``-`` is parsed by git as an OPTION, not
a ref, even though the argv is a list and shell=False. So ``?from=--output=/p``
turns into ``git diff --output=/p <to>`` — an arbitrary-file write as the
Django process user (CWE-88 argument injection → file write).

The endpoint is reachable UNAUTHENTICATED for any public project
(permissions.check_project_read_access returns True for an anonymous request
when project.visibility == "public"), so the ref is validated and rejected
rather than merely quoted. See sec-develop-codeql-red-210-new-alerts (alert
#8552).
"""
from __future__ import annotations

import pytest

from apps.infra.project_app.views.repository.api.git_history import (
    _is_valid_git_ref,
)

pytestmark = pytest.mark.security

# Every one of these would be parsed by git as an OPTION in a ref position.
INJECTING_REFS = [
    "--output=/tmp/pwned",       # git diff --output= : arbitrary file write
    "--output=/etc/cron.d/x",
    "-O/tmp/orderfile",          # short option form
    "--no-index",                # switches diff into two-path mode
    "--ext-diff",                # enables external diff driver
    "-",                         # bare leading dash
    "..--output=/tmp/x",         # leading dot (range foothold) + option
]

# Legitimate single revisions this endpoint is documented to receive.
VALID_REFS = [
    "HEAD",
    "HEAD~1",
    "HEAD^",
    "main",
    "0123456789abcdef0123456789abcdef01234567",  # full sha
    "abc1234",                                    # short sha
    "feature/new-thing",                          # namespaced branch
    "refs/tags/v1.0.0",
    "origin/develop",
]


@pytest.mark.parametrize("ref", INJECTING_REFS)
def test_option_injecting_ref_is_rejected(ref):
    """A ref that git would read as an option must not validate."""
    # Arrange
    hostile = ref
    # Act
    accepted = _is_valid_git_ref(hostile)
    # Assert
    assert accepted is False


@pytest.mark.parametrize("ref", VALID_REFS)
def test_legitimate_ref_is_accepted(ref):
    """A syntactically normal revision must still validate."""
    # Arrange
    legit = ref
    # Act
    accepted = _is_valid_git_ref(legit)
    # Assert
    assert accepted is True


def test_empty_ref_is_not_valid():
    """The empty string is 'not supplied', handled by the caller — never a ref."""
    # Arrange
    empty = ""
    # Act
    accepted = _is_valid_git_ref(empty)
    # Assert
    assert accepted is False
