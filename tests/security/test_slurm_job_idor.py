#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Security regression barrier for the SLURM job API cross-tenant IDOR.

``apps/workspace/console_app/job_api_views.py`` exposes job status /
cancel / output endpoints keyed on a RAW numeric ``job_id`` off the wire.
There is NO DB record mapping a job id to its owner, so before this fix
``api_cancel_job`` called ``cancel_job(int(job_id))`` with no ownership
check -- any authenticated user could cancel ANY user's job by iterating
ids (and read any job's state via ``api_job_status``). The fix authorizes
every id-addressed endpoint through
``console_app.services.job_ownership.job_belongs_to_user``, which resolves
the id to its SLURM job NAME and matches the owner's username prefix.

These tests are DB-FREE and MOCK-FREE by mandate (the CI "Security
Regression Gate" runs with no Postgres and forbids ``unittest.mock``):

* A -- pure-function tests of ``name_belongs_to_user`` (the module is
  imported in isolation, no ``apps.*`` package chain, no Django).
* B -- ``job_belongs_to_user`` against a 5-line plain stub class (no
  framework mock), incl. deny-on-gone.
* C -- a static wiring scan (tokenize-strip comments/strings, then
  substring match) proving each endpoint keeps its gate + 404 and that
  ``api_submit_job`` stamps the ``scitex_<username>_`` prefix -- so the
  gates cannot be silently deleted while a comment keeps them "documented".
"""
from __future__ import annotations

import ast
import importlib.util
import io
import tokenize
from pathlib import Path

import pytest

pytestmark = pytest.mark.security

_REPO = Path(__file__).resolve().parents[2]
_CONSOLE = _REPO / "apps" / "workspace" / "console_app"
_OWNERSHIP_PY = _CONSOLE / "services" / "job_ownership.py"
_VIEWS_PY = _CONSOLE / "job_api_views.py"


def _load_ownership():
    """Import job_ownership.py in isolation -- no apps.* chain, no Django, no DB."""
    spec = importlib.util.spec_from_file_location(
        "job_ownership_under_test", _OWNERSHIP_PY
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_own = _load_ownership()
name_belongs_to_user = _own.name_belongs_to_user
job_belongs_to_user = _own.job_belongs_to_user


# ---------------------------------------------------------------------------
# A. Pure predicate: name_belongs_to_user
# ---------------------------------------------------------------------------
def test_name_matches_compute_job_of_same_user():
    # Breakage caught: prefix match for compute jobs stops working.
    # Arrange
    name, username = "scitex_alice_proj1", "alice"
    # Act
    owned = name_belongs_to_user(name, username)
    # Assert
    assert owned is True


def test_name_rejects_compute_job_of_other_user():
    # Breakage caught: a user could claim another user's job (cross-tenant).
    # Arrange
    name, username = "scitex_alice_proj1", "bob"
    # Act
    owned = name_belongs_to_user(name, username)
    # Assert
    assert owned is False


def test_name_matches_terminal_allocation_of_same_user():
    # Breakage caught: terminal-allocation naming convention dropped.
    # Arrange
    name, username = "scitex-hub-terminal-alice", "alice"
    # Act
    owned = name_belongs_to_user(name, username)
    # Assert
    assert owned is True


def test_name_rejects_unstamped_job():
    # Documents the pre-companion-fix gap: an un-prefixed job matches nobody.
    # Arrange
    name, username = "scitex_job", "alice"
    # Act
    owned = name_belongs_to_user(name, username)
    # Assert
    assert owned is False


def test_name_rejects_username_prefix_sibling():
    # Breakage caught: the trailing "_" boundary; else "alice" claims "alicia".
    # Arrange
    name, username = "scitex_alicia_p", "alice"
    # Act
    owned = name_belongs_to_user(name, username)
    # Assert
    assert owned is False


def test_name_rejects_empty_name():
    # Breakage caught: an empty/absent name must never authorize.
    # Arrange
    name, username = "", "alice"
    # Act
    owned = name_belongs_to_user(name, username)
    # Assert
    assert owned is False


# ---------------------------------------------------------------------------
# B. job_belongs_to_user against a plain stub (NO framework mock)
# ---------------------------------------------------------------------------
class _StubSlurm:
    """5-line stand-in for SlurmManager.list_jobs -- canned queue, no mock."""

    def list_jobs(self, state=None):
        return {"jobs": [{"job_id": 42, "name": "scitex_alice_p"}]}


def test_job_owned_by_matching_user_resolves_true():
    # Breakage caught: owner is denied access to their own job (self-lockout).
    # Arrange
    slurm = _StubSlurm()
    # Act
    owned = job_belongs_to_user(slurm, 42, "alice")
    # Assert
    assert owned is True


def test_job_owned_by_other_user_resolves_false():
    # Breakage caught: cross-tenant access to a job owned by someone else.
    # Arrange
    slurm = _StubSlurm()
    # Act
    owned = job_belongs_to_user(slurm, 42, "bob")
    # Assert
    assert owned is False


def test_absent_job_is_denied():
    # Breakage caught: a job that left the queue must DENY, not fall open.
    # Arrange
    slurm = _StubSlurm()
    # Act
    owned = job_belongs_to_user(slurm, 99, "alice")
    # Assert
    assert owned is False


# ---------------------------------------------------------------------------
# C. Static wiring scan of job_api_views.py
# ---------------------------------------------------------------------------
def _strip_comments_and_strings(source: str) -> str:
    """Return ``source`` with COMMENT and STRING tokens removed, re-joined.

    A gate named only in a comment/docstring must NOT satisfy the scan --
    only LIVE code counts (same technique as test_idor_ownership). On an
    unparseable file, fall back to raw text (fail loud, never mask).
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


def _function_source(source: str, func_name: str) -> str:
    """Raw source segment of a top-level function (decorators excluded)."""
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == func_name:
            seg = ast.get_source_segment(source, node)
            if seg is not None:
                return seg
    raise AssertionError(f"function {func_name} not found in job_api_views.py")


_VIEWS_SRC = _VIEWS_PY.read_text(encoding="utf-8")
_ID_ENDPOINTS = ["api_cancel_job", "api_job_status", "api_job_output"]


@pytest.mark.parametrize("endpoint", _ID_ENDPOINTS)
def test_endpoint_keeps_ownership_gate(endpoint):
    # Breakage caught: silent removal of the IDOR gate from an id-addressed
    # endpoint (a comment naming it does not count -- strings are stripped).
    # Arrange
    live = _strip_comments_and_strings(_function_source(_VIEWS_SRC, endpoint))
    # Act
    gate_present = "job_belongs_to_user" in live
    # Assert
    assert gate_present, (
        f"IDOR regression: {endpoint} no longer calls job_belongs_to_user in "
        f"live code -- any authenticated user can address another tenant's job."
    )


@pytest.mark.parametrize("endpoint", _ID_ENDPOINTS)
def test_endpoint_answers_nonowner_with_404(endpoint):
    # Breakage caught: dropping the 404 (e.g. to 403/200) would leak whether a
    # job id exists for another tenant -- existence disclosure.
    # Arrange
    live = _strip_comments_and_strings(_function_source(_VIEWS_SRC, endpoint))
    # Act
    returns_404 = "status=404" in live
    # Assert
    assert returns_404, (
        f"{endpoint} must answer a non-owned job with 404 (not 403/200), so it "
        f"is indistinguishable from a nonexistent job (no existence disclosure)."
    )


def test_submit_job_stamps_username_prefix():
    # Breakage caught: dropping the scitex_<username>_ stamp -- owners would be
    # locked out of their OWN jobs and api_user_jobs would not list them.
    # Arrange
    raw_submit = _function_source(_VIEWS_SRC, "api_submit_job")
    # Needle assembled per spec (f"scitex_{" + "username") to avoid embedding
    # the whole literal while still binding prefix AND username wiring.
    needle = 'f"scitex_{' + "request.user.username"
    # Act
    stamped = needle in raw_submit
    # Assert
    assert stamped, (
        "api_submit_job must force the SLURM job name to start with "
        'f"scitex_{request.user.username}_" so the ownership gate admits the '
        "owner and api_user_jobs can list the job."
    )


# ---------------------------------------------------------------------------
# C (non-vacuity): the stripper actually removes comment/string mentions
# ---------------------------------------------------------------------------
def test_stripper_drops_gate_named_only_in_comment():
    # Non-vacuity: a gate mentioned only in a comment does NOT satisfy the scan.
    # Arrange
    src = "def f():\n    # job_belongs_to_user(x) status=404\n    return 1\n"
    # Act
    stripped = _strip_comments_and_strings(src)
    # Assert
    assert "job_belongs_to_user" not in stripped


def test_stripper_keeps_live_gate_call():
    # Non-vacuity: a live gate call survives stripping, so the scan can see it.
    # Arrange
    src = "def f():\n    if not job_belongs_to_user(s, i, u):\n        return 404\n"
    # Act
    stripped = _strip_comments_and_strings(src)
    # Assert
    assert "job_belongs_to_user" in stripped


# EOF
