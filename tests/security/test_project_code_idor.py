"""Regression: the project_code view must gate the project by ownership (IDOR).

`console_app` project_code(request, project_id) fetches a Project by its RAW id
(get_object_or_404(Project, id=project_id)) and renders that project's code
interface. The id comes straight off the URL, so the fetch alone proves nothing
about ownership — without an authorization check, ANY authenticated user could
open ANY tenant's project by iterating project_id (a cross-tenant IDOR; tenant
isolation is the #1 mandate). The fix gates access on the same rule as
file_content.py: owner OR collaborator OR public, else Http404.

Delete that check and the endpoint is a cross-tenant read again, so this gate
must be loud and blocking. There are TWO copies of the view (a known duplicate),
both must keep the guard. The detector strips COMMENT/STRING tokens before
matching (like test_no_prefix_path_containment) so a guard named only in a
comment/docstring cannot keep the gate green — "a review that reads code is not
a test that runs it". DB-free + mock-free (the security-regression CI job has no
Postgres and forbids mocks).
"""
from __future__ import annotations

import io
import tokenize
from pathlib import Path

import pytest

pytestmark = pytest.mark.security

_CONSOLE = Path(__file__).resolve().parents[2] / "apps" / "workspace" / "console_app"
_PROJECT_CODE_VIEWS = (
    _CONSOLE / "views" / "project_views.py",
    _CONSOLE / "project_views.py",
)
# The tenant-isolation barrier: the owner/collaborator/public ownership check.
_GUARD = "project.collaborators.all()"


def _live_code(source: str) -> str:
    """Return ``source`` with COMMENT and STRING tokens dropped (tokens re-joined).

    A guard named only in a comment or docstring must NOT satisfy the gate, so
    comments and strings are removed before matching. On an unparseable file we
    fall back to the raw text rather than silently passing (fail loud, no mask).
    """
    try:
        toks = list(tokenize.generate_tokens(io.StringIO(source).readline))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return source
    return "".join(
        t.string for t in toks if t.type not in (tokenize.COMMENT, tokenize.STRING)
    )


def test_project_code_view_keeps_ownership_guard():
    # Arrange
    code = _live_code(_PROJECT_CODE_VIEWS[0].read_text(encoding="utf-8"))
    # Act
    guarded = _GUARD in code
    # Assert
    assert guarded, (
        f"IDOR regression: {_PROJECT_CODE_VIEWS[0]} fetches a Project by raw "
        "project_id and renders its code interface. The owner/collaborator/public "
        "ownership check is the only tenant-isolation barrier — restore it "
        "(a code comment naming it does not count)."
    )


def test_console_project_code_duplicate_keeps_ownership_guard():
    # Arrange
    code = _live_code(_PROJECT_CODE_VIEWS[1].read_text(encoding="utf-8"))
    # Act
    guarded = _GUARD in code
    # Assert
    assert guarded, (
        f"IDOR regression: {_PROJECT_CODE_VIEWS[1]} (the duplicate project_code "
        "copy) fetches a Project by raw project_id with no ownership check — "
        "restore the owner/collaborator/public gate."
    )


def test_stripper_ignores_a_guard_named_only_in_a_comment():
    # Arrange
    src = "def f(project, request):\n    # request.user in project.collaborators.all()\n    return True\n"
    # Act
    stripped = _live_code(src)
    # Assert
    assert _GUARD not in stripped


def test_stripper_keeps_a_live_guard_call():
    # Arrange
    src = "def f(project, request):\n    if request.user in project.collaborators.all():\n        return True\n"
    # Act
    stripped = _live_code(src)
    # Assert
    assert _GUARD in stripped
