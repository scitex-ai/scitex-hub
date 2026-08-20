"""Mechanical regression barrier for the IDOR (insecure direct object reference) class.

The workspace editor's file-content and file-save APIs fetch a Project by its
RAW id -- ``Project.objects.select_related("owner").get(id=project_id)`` -- the
classic IDOR-prone shape: the primary key comes straight off the wire, so the
fetch alone proves nothing about ownership. What keeps these two endpoints
tenant-isolated is the authorization check wired in AFTER the fetch and BEFORE
the file is read / written:

    file_save.py    : ``if not project.can_edit(request.user): return 403``   (write)
    file_content.py : ``request.user == project.owner
                        or request.user in project.collaborators.all()
                        or project.visibility == "public"``  else 403         (read)

Delete either check and the endpoint becomes a CROSS-TENANT IDOR: any
authenticated user could overwrite (file_save) or read (file_content) ANY
tenant's project files by iterating ``project_id``. Tenant isolation is the #1
mandate, so a regression here must be loud and blocking -- a required check, not
a comment a future edit can quietly drop.

Both source files ALSO name their guard in a nearby CODE COMMENT
("via project.can_edit(request.user); this confines the write ..."). A gate that
a leftover comment keeps green is not a gate -- "a review that reads code is not
a test that runs it". So the detector strips COMMENT and STRING tokens before
matching (same technique as test_no_prefix_path_containment): only LIVE code can
satisfy the gate. The non-vacuity self-tests below prove that stripping works,
i.e. removing the live check while leaving the comment DOES flip this red.
"""
from __future__ import annotations

import io
import tokenize
from pathlib import Path

import pytest

pytestmark = pytest.mark.security

_APPS = Path(__file__).resolve().parents[2] / "apps"
_WS_VIEWS = _APPS / "infra" / "workspace_api" / "views"
FILE_SAVE = _WS_VIEWS / "file_save.py"
FILE_CONTENT = _WS_VIEWS / "file_content.py"


def _code_text(source: str) -> str:
    """Return ``source`` with COMMENT and STRING tokens removed, tokens re-joined.

    A guard removed from live code but still NAMED in a comment or string must
    NOT keep the gate green, so comments and strings are dropped before matching.
    Guard tokens (``project`` ``.`` ``can_edit`` ``(`` ...) are contiguous within
    a line, so the joined text preserves the substring we assert on. On an
    unparseable file we fall back to the raw text rather than silently passing
    (fail loud, never mask).
    """
    try:
        toks = list(tokenize.generate_tokens(io.StringIO(source).readline))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return source
    return "".join(
        t.string
        for t in toks
        if t.type not in (tokenize.COMMENT, tokenize.STRING)
    )


def test_file_save_write_endpoint_keeps_can_edit_ownership_guard():
    """Write-IDOR gate: api_save_file must gate its Project(id=...) fetch on can_edit."""
    # Arrange
    code = _code_text(FILE_SAVE.read_text(encoding="utf-8"))
    # Act
    guard_present = "project.can_edit(request.user)" in code
    # Assert
    assert guard_present, (
        "IDOR regression: apps/infra/workspace_api/views/file_save.py fetches a "
        "Project by raw id (Project.objects...get(id=project_id)) then writes "
        "caller-supplied content to that project's filesystem. The "
        "'if not project.can_edit(request.user): return 403' ownership check is "
        "the ONLY thing stopping any authenticated user from overwriting ANY "
        "tenant's files by iterating project_id. Restore the live check "
        "(a code comment naming it does not count)."
    )


def test_file_content_read_endpoint_keeps_owner_collaborator_guard():
    """Read-IDOR gate: api_get_file_content must gate its Project(id=...) fetch on ownership."""
    # Arrange
    code = _code_text(FILE_CONTENT.read_text(encoding="utf-8"))
    # Act
    guard_present = "project.collaborators.all()" in code
    # Assert
    assert guard_present, (
        "IDOR regression: apps/infra/workspace_api/views/file_content.py fetches "
        "a Project by raw id then returns its file bytes. The owner/collaborator/"
        "public read check (request.user == project.owner or request.user in "
        "project.collaborators.all() or project.visibility == 'public') is the "
        "only tenant-isolation barrier before the read. Restore the live check "
        "(a code comment naming it does not count)."
    )


def test_stripper_ignores_guard_named_only_in_a_comment():
    """Non-vacuity: a guard named only in a comment does NOT satisfy the gate."""
    # Arrange
    src = "def f(project, request):\n    # if not project.can_edit(request.user): 403\n    return True\n"
    # Act
    stripped = _code_text(src)
    # Assert
    assert "can_edit" not in stripped


def test_stripper_ignores_guard_named_only_in_a_string():
    """Non-vacuity: a guard named only in a string literal does NOT satisfy the gate."""
    # Arrange
    src = 'def f():\n    doc = "call project.can_edit(request.user) here"\n    return doc\n'
    # Act
    stripped = _code_text(src)
    # Assert
    assert "can_edit" not in stripped


def test_stripper_keeps_a_live_guard_call():
    """Non-vacuity: a live guard call survives stripping, so the gate can see real code."""
    # Arrange
    src = "def f(project, request):\n    if not project.can_edit(request.user):\n        return 403\n    return True\n"
    # Act
    stripped = _code_text(src)
    # Assert
    assert "project.can_edit(request.user)" in stripped
