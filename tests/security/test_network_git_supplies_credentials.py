#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: ./tests/security/test_network_git_supplies_credentials.py

"""Every git operation that TALKS TO GITEA must carry a per-op credential.

WHY THIS FILE EXISTS
--------------------
Hub clones a user's project from Gitea and DELIBERATELY records a
credential-less ``origin``. ``.git/config`` is bind-mounted read/write into
the user's Apptainer console at ``/workspace``, so a token written there
leaks the platform ADMIN credential across tenants
(sec-gitea-admin-token-plaintext-in-user-gitconfig). The credential is
instead handed to each git process through the ENVIRONMENT --
``build_gitea_auth_env()`` -> a URL-scoped ``http.<gitea>.extraHeader``.

That design carries a standing obligation, stated in the clone site's own
comment in ``project_initialization.py``::

    Push/pull re-supply the token per-op the same way
    (see git_service.build_gitea_auth_env).

A network git call that omits ``env=`` therefore has NO credential at all --
not a stale one, not a wrong one, none -- and git falls back to prompting for
a username a server process can never read.

MEASURED, production ``scitex-hub-prod-celery_worker_vis-1``, 2026-09-06
00:12Z, over the 19 h the post-rebuild container had been up::

    "Could not push to Gitea"                    1044
    "verified clean and returned to pool"        1044   <- positive control
    a sentinel string that must not appear          0   <- negative control

    fatal: could not read Username for 'http://gitea:3000':
    No such device or address

A 1:1 ratio: EVERY visitor workspace reset failed its push. The repo create,
delete and clone in those same resets all succeeded -- they go through the
API client and the authenticated clone -- so the Gitea integration was
working everywhere except the one call that had no ``env=``.

These tests pin the PROPERTY rather than that one call site, because the same
omission was present at three sites when it was found.

WHAT THIS FILE DOES NOT CHECK (declared, not overlooked)
--------------------------------------------------------
1. Only ``subprocess.run`` with a LITERAL argv list is classified. A call
   built at runtime (``["git"] + args``) cannot be judged by value; the one
   such wrapper in the tree is checked by name in
   ``test_the_run_git_command_wrapper_supplies_an_auth_env``, but a NEW
   wrapper would be invisible here.
2. ``subprocess.Popen`` / ``check_output`` / ``os.system`` / GitPython are
   not scanned. Nothing in ``apps/`` uses them for network git today; that is
   a fact about today, not a property this file holds.
3. Passing SOME env satisfies these tests. They prove an environment was
   supplied, never that it carries the Gitea credential -- that is
   ``build_gitea_auth_env``'s own contract, covered in
   ``test_gitea_token_gitconfig.py``.

Card: hub-visitor-workspace-gitea-push-fails-46-of-46-20260828
"""

from __future__ import annotations

import ast
from pathlib import Path

APPS_ROOT = Path(__file__).resolve().parents[2] / "apps"

#: git verbs that open a connection to Gitea and therefore need a credential.
NETWORK_VERBS = frozenset({"push", "pull", "fetch", "clone", "ls-remote"})

#: The wrapper whose argv is built at runtime, so the AST scan cannot judge it.
WRAPPER_FILE = (
    APPS_ROOT / "infra" / "project_app" / "views" / "repository" / "api" / "git_utils.py"
)
WRAPPER_NAME = "run_git_command"

#: Below this, the scan found too little to be believed -- an empty walk must
#: fail rather than read as "no offenders". Set well under the count observed
#: when the file was written (7) so ordinary deletions do not break the suite.
MIN_EXPECTED_NETWORK_GIT_CALLS = 3


def _is_subprocess_run(call: ast.Call) -> bool:
    """True for ``subprocess.run(...)``."""
    func = call.func
    return (
        isinstance(func, ast.Attribute)
        and func.attr == "run"
        and isinstance(func.value, ast.Name)
        and func.value.id == "subprocess"
    )


def _literal_str_list(node: ast.AST) -> list[str] | None:
    """Elements of a list/tuple literal of plain strings, else None."""
    if not isinstance(node, (ast.List, ast.Tuple)):
        return None
    out: list[str] = []
    for element in node.elts:
        if isinstance(element, ast.Constant) and isinstance(element.value, str):
            out.append(element.value)
        else:
            return None
    return out


def _network_git_calls(path: Path) -> list[tuple[int, str, bool]]:
    """``(lineno, verb, supplies_env)`` per literal network-git subprocess."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: list[tuple[int, str, bool]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not _is_subprocess_run(node):
            continue
        if not node.args:
            continue
        argv = _literal_str_list(node.args[0])
        if not argv or argv[0] != "git":
            continue
        verbs = [token for token in argv[1:] if token in NETWORK_VERBS]
        if not verbs:
            continue
        supplies_env = any(keyword.arg == "env" for keyword in node.keywords)
        found.append((node.lineno, verbs[0], supplies_env))
    return found


def _scan_apps() -> list[tuple[str, int, str, bool]]:
    """``(relpath, lineno, verb, supplies_env)`` for all of ``apps/``."""
    calls: list[tuple[str, int, str, bool]] = []
    for py_file in sorted(APPS_ROOT.rglob("*.py")):
        relpath = str(py_file.relative_to(APPS_ROOT.parent))
        for lineno, verb, supplies_env in _network_git_calls(py_file):
            calls.append((relpath, lineno, verb, supplies_env))
    return calls


def test_the_scan_actually_finds_network_git_call_sites():
    """CONTROL: an empty walk must fail, not pass as 'no offenders'."""
    # Arrange
    floor = MIN_EXPECTED_NETWORK_GIT_CALLS

    # Act
    calls = _scan_apps()

    # Assert
    assert len(calls) >= floor, (
        f"the scan found only {len(calls)} network-git call site(s) under "
        f"{APPS_ROOT}; below {floor} the scan is not measuring the tree and "
        "its green means nothing"
    )


def test_every_network_git_call_supplies_an_auth_env():
    """A git op that reaches Gitea must be handed a credential environment."""
    # Arrange
    calls = _scan_apps()

    # Act
    offenders = [
        f"{relpath}:{lineno} git {verb}"
        for relpath, lineno, verb, supplies_env in calls
        if not supplies_env
    ]

    # Assert
    assert offenders == [], (
        "these git operations reach Gitea with no credential, so git prompts "
        "for a username no server process can answer (prod logged 1044 such "
        "failed pushes in 19 h): " + "; ".join(offenders)
    )


def test_the_run_git_command_wrapper_supplies_an_auth_env():
    """The runtime-argv wrapper the value scan cannot classify."""
    # Arrange
    tree = ast.parse(WRAPPER_FILE.read_text(encoding="utf-8"), filename=str(WRAPPER_FILE))
    wrapper = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == WRAPPER_NAME
    )

    # Act
    runs_without_env = [
        node.lineno
        for node in ast.walk(wrapper)
        if isinstance(node, ast.Call)
        and _is_subprocess_run(node)
        and not any(keyword.arg == "env" for keyword in node.keywords)
    ]

    # Assert
    assert runs_without_env == [], (
        f"{WRAPPER_NAME} builds its argv at runtime, so callers passing "
        f"'push'/'pull'/'fetch' are invisible to the value scan; it must "
        f"therefore supply the auth env itself (lines: {runs_without_env})"
    )


# EOF
