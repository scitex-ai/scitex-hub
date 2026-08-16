#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mechanical regression barrier for CSRF-exempt session-authenticated views.

A view that is BOTH ``@login_required`` (authenticated via the session cookie)
AND ``@csrf_exempt`` is CSRF-vulnerable: an attacker page can forge a
state-changing request that rides the victim's session cookie, and the
``@csrf_exempt`` decorator waves the token check that would otherwise stop it.
Legitimately-exempt endpoints authenticate with a Bearer token / webhook
signature / api-key or are anonymous pre-auth flows -- none of those carry
``@login_required``, so the login_required+csrf_exempt PAIR is the fingerprint
of the vulnerable class. Ten such views were de-exempted (job submit/cancel,
external_proxy, scholar api-key create/delete/update, repository-connection
create, save_user_preferences, test_api_key, and the hybrid
save_source_preferences) -- see card hub-csrf-exempt-session-views.

This test FAILS if the pairing reappears anywhere under ``apps/``, so a
regression is loud and blocking (it runs in the required Security Regression
Gate), not a written warning a future edit can silently ignore -- "a gate that
cannot fail is not a gate". The ALLOWLIST is intentionally EMPTY: no
session-authenticated state-changing view may be csrf_exempt.

Pure ``ast`` only -- no Postgres, no ``unittest.mock`` (STX-NM001/NM003) -- so
it runs in the DB-free, mock-free security gate.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.security

_REPO_ROOT = Path(__file__).resolve().parents[2]
_APPS_ROOT = _REPO_ROOT / "apps"

_LOGIN_REQUIRED = "login_required"
_CSRF_EXEMPT = "csrf_exempt"


def _decorator_name(node: ast.expr) -> str | None:
    """Resolve a decorator expression to its simple name.

    A decorator may be a bare ``Name`` (``@csrf_exempt``), an ``Attribute``
    (``@decorators.csrf_exempt`` -> ``csrf_exempt``), or a ``Call`` wrapping
    either (``@require_http_methods(...)``). Anything else yields ``None``.
    """
    if isinstance(node, ast.Call):
        node = node.func
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _decorator_names(func: ast.AST) -> set[str]:
    """Return the set of simple decorator names on a function definition."""
    return {
        name
        for dec in getattr(func, "decorator_list", [])
        if (name := _decorator_name(dec)) is not None
    }


def find_session_csrf_exempt(source: str) -> list[tuple[int, str]]:
    """Return ``(lineno, funcname)`` for each login_required+csrf_exempt func.

    On an unparseable file we raise rather than silently skip it (fail loud,
    never mask a file the gate is supposed to police).
    """
    tree = ast.parse(source)
    hits: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            names = _decorator_names(node)
            if {_LOGIN_REQUIRED, _CSRF_EXEMPT} <= names:
                hits.append((node.lineno, node.name))
    return hits


def test_no_login_required_view_is_csrf_exempt_under_apps():
    """The real gate: no ``@login_required`` view under apps/ is ``@csrf_exempt``."""
    # Arrange
    py_files = sorted(_APPS_ROOT.rglob("*.py"))
    # Act
    offenders = [
        f"{py.relative_to(_REPO_ROOT)}:{lineno}:{name}"
        for py in py_files
        for lineno, name in find_session_csrf_exempt(py.read_text(encoding="utf-8"))
    ]
    # Assert
    assert offenders == [], (
        "A session-authenticated (@login_required) view is @csrf_exempt again. "
        "Session cookie + csrf_exempt lets an attacker page forge state-changing "
        "requests with the victim's cookie. Remove @csrf_exempt (the browser "
        "callers send X-CSRFToken via static/shared/ts/utils/csrf.ts). "
        "Allowlist is EMPTY by design. Offenders (file:lineno:func):\n  "
        + "\n  ".join(offenders)
    )


def test_save_source_preferences_is_not_csrf_exempt():
    """The hybrid view (no @login_required) must also drop @csrf_exempt.

    ``save_source_preferences`` writes to the DB for authenticated users but
    lacks ``@login_required``, so the login_required+csrf_exempt rule above
    does NOT catch it -- assert it specifically here.
    """
    # Arrange
    path = (
        _APPS_ROOT
        / "workspace"
        / "scholar_app"
        / "views"
        / "search"
        / "preferences.py"
    )
    tree = ast.parse(path.read_text(encoding="utf-8"))
    # Act
    funcs = [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == "save_source_preferences"
    ]
    decorators = {name for func in funcs for name in _decorator_names(func)}
    # Assert
    assert funcs and _CSRF_EXEMPT not in decorators, (
        "save_source_preferences must not be @csrf_exempt: it writes "
        "preferred_sources to the DB for authenticated users, and its browser "
        "caller source-preferences.ts already sends X-CSRFToken. Decorators "
        f"found: {sorted(decorators)} (empty list => function not found)."
    )


def test_detector_flags_function_with_both_decorators():
    """Non-vacuity: the detector FLAGS a func with both decorators (gate can fail)."""
    # Arrange
    src = (
        "@login_required\n"
        "@csrf_exempt\n"
        "@require_http_methods(['POST'])\n"
        "def vulnerable(request):\n"
        "    return None\n"
    )
    # Act
    hits = find_session_csrf_exempt(src)
    # Assert
    assert hits == [(4, "vulnerable")], (
        "detector missed a function decorated with both login_required and "
        "csrf_exempt -- the gate would be vacuous"
    )


def test_detector_ignores_function_with_only_login_required():
    """Non-vacuity: a @login_required-only func is NOT flagged (no false positive)."""
    # Arrange
    src = "@login_required\ndef safe(request):\n    return None\n"
    # Act
    hits = find_session_csrf_exempt(src)
    # Assert
    assert hits == [], "detector false-positived on a login_required-only view"


def test_detector_ignores_function_with_only_csrf_exempt():
    """Non-vacuity: a @csrf_exempt-only func (e.g. Bearer/webhook) is NOT flagged."""
    # Arrange
    src = "@csrf_exempt\ndef webhook(request):\n    return None\n"
    # Act
    hits = find_session_csrf_exempt(src)
    # Assert
    assert hits == [], "detector false-positived on a csrf_exempt-only view"


# EOF
