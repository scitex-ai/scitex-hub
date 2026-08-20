#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/develop/test_interactive_prompt_call_sites.py

"""CLI spec §2 — STATIC scan for interactive-prompt call sites.

WHY THIS EXISTS, given that ``test_no_interactive_prompts.py`` already
covers §2 behaviourally: the two cannot catch each other's misses.

  * That file is BEHAVIOURAL and PER-COMMAND. It drives specific
    commands through ``CliRunner`` with ``input=""`` and asserts they
    fail fast. A prompt in a command it does not invoke is invisible to
    it — which is exactly what happened: three real ``click.prompt`` /
    ``click.confirm`` sites lived in ``_cli/_auth/_login.py`` and
    ``_cli/_flags.py`` while that file exercised ``_cli/_gitea_auth``,
    a different login path entirely.
  * This file is STATIC and REPO-WIDE. It enumerates every call site and
    fails with ``file:line``, so a new prompt cannot arrive unnoticed
    in a command nobody thought to test.

The other reason it is static: the ecosystem auditor already covers
§2, but it only RUNS when its own optional dependencies happen to be
importable. When they are absent it reports ``not-auditable`` and the
run goes green over an ungraded CLI — measured 2026-08-09, hiding these
same three findings. A scan living in this repo's own suite has no such
dependency and cannot silently self-disable, which is the whole point of
preferring a mechanical barrier to a check that can quietly stop
checking.

WHAT AN ALLOWLIST ENTRY MEANS: "this prompt is intended AND is guarded
so it cannot block a non-interactive caller." It is not "we accept this
violation." Every entry names the guard, and the guard itself is proved
by a behavioural test elsewhere — an allowlist that only asserts good
intentions would be this gate's own version of going quietly green.

WHAT THIS DOES **NOT** COVER — stated so nobody reads a green run as
"this repo cannot hang on stdin", which is a stronger claim than the
scan supports:

  * Only ``src/scitex_hub``. Django code under ``apps/`` and helper
    scripts are not scanned; they do not use click today, and widening
    the sweep should come with allowlist review rather than silently.
  * Only ``click.prompt`` / ``click.confirm``. Bare ``input()``,
    ``getpass.getpass()`` and ``sys.stdin.read()`` block just as hard
    and are NOT detected.
  * Static reachability only. It proves a call site is declared
    intentional, never that its guard is correct — that is the
    behavioural test's job, and an allowlist entry without one is a
    gap, not a pass.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

# tests/develop/<this file> -> repo root is 3 levels up.
#
# Lives in tests/develop/ with the repo's other whole-tree gates
# (test_audit.py, test_ci_bypasses_are_justified.py,
# test_worktrees_are_ignored_by_tracked_rule.py) rather than under
# tests/scitex_hub/, because it asserts a property of the TREE, not of
# one source module. Placing it in the mirror tree also made it an
# orphan-test-file (PS-204) with no source counterpart to mirror — a
# measured +1 on the audit's masked-violation ceiling, which is the
# structure convention telling the truth about where this belongs.
REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src" / "scitex_hub"

#: Callables that read from stdin and therefore can block an agent.
PROMPT_NAMES = frozenset({"prompt", "confirm"})

#: (posix relpath from repo root, enclosing function) -> why it is allowed.
#:
#: Keyed by FUNCTION rather than line number so ordinary edits above a
#: call site do not churn this list, while a prompt added to a DIFFERENT
#: function still fails — the case worth catching.
ALLOWED_PROMPT_SITES: dict[tuple[str, str], str] = {
    (
        "src/scitex_hub/_cli/_flags.py",
        "confirm_or_abort",
    ): (
        "The sanctioned shared confirmation helper. Prompts only after "
        "checking --yes, --dry-run and sys.stdin.isatty(), so a "
        "non-interactive caller never reaches the prompt. This is the "
        "function §2 wants destructive verbs to route through."
    ),
    (
        "src/scitex_hub/_cli/_auth/_login.py",
        "auth_login",
    ): (
        "Interactive credential entry for humans at a terminal. Guarded "
        "by an explicit sys.stdin.isatty() refusal that raises "
        "click.UsageError (exit 2) naming --user/--password before any "
        "prompt is reached; proved by "
        "tests/scitex_hub/_cli/_auth/test__login.py::"
        "test_login_without_tty_refuses_instead_of_prompting."
    ),
}


def _enclosing_function(node: ast.AST, parents: dict[ast.AST, ast.AST]) -> str:
    """Name of the nearest enclosing function, or ``"<module>"``."""
    current = parents.get(node)
    while current is not None:
        if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return current.name
        current = parents.get(current)
    return "<module>"


def _is_prompt_call(node: ast.AST) -> str | None:
    """Return the called name if *node* is a click prompt/confirm call."""
    if not isinstance(node, ast.Call):
        return None
    func = node.func
    # click.prompt(...) / click.confirm(...)
    if isinstance(func, ast.Attribute) and func.attr in PROMPT_NAMES:
        if isinstance(func.value, ast.Name) and func.value.id == "click":
            return f"click.{func.attr}"
    # bare prompt(...) / confirm(...) from `from click import prompt`
    if isinstance(func, ast.Name) and func.id in PROMPT_NAMES:
        return func.id
    return None


def _collect_prompt_sites() -> list[tuple[str, str, int, str]]:
    """Every prompt call site as (relpath, function, lineno, called)."""
    found: list[tuple[str, str, int, str]] = []
    for path in sorted(SRC_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        parents: dict[ast.AST, ast.AST] = {}
        for parent in ast.walk(tree):
            for child in ast.iter_child_nodes(parent):
                parents[child] = parent
        rel = path.relative_to(REPO_ROOT).as_posix()
        for node in ast.walk(tree):
            called = _is_prompt_call(node)
            if called is None:
                continue
            found.append((rel, _enclosing_function(node, parents), node.lineno, called))
    return found


def test_src_tree_is_scannable():
    """The scan reads a real tree — an empty sweep must not read as clean.

    A path typo would make every assertion below vacuously true, which is
    the failure mode this whole file exists to prevent.
    """
    # Arrange
    src_root = SRC_ROOT
    # Act
    module_count = len(list(src_root.rglob("*.py")))
    # Assert
    assert module_count > 0, (
        f"no Python modules found under {SRC_ROOT} — the scan is looking at "
        "the wrong tree, so its 'no unguarded prompts' verdict is meaningless. "
        "Fix REPO_ROOT's parents[] depth in this file."
    )


def test_scanner_detects_a_known_prompt():
    """Control: the detector finds a call site we know is there.

    Without this, a broken matcher reports zero findings and the gate goes
    green precisely when it has stopped working.
    """
    # Arrange
    expected_site = ("src/scitex_hub/_cli/_flags.py", "confirm_or_abort")
    # Act
    got_sites = {(rel, func) for rel, func, _, _ in _collect_prompt_sites()}
    # Assert
    assert expected_site in got_sites, (
        "the prompt detector found no click.confirm in _flags.py, where one "
        "is known to exist. The AST matcher is broken; every other assertion "
        "in this file is now vacuous."
    )


def test_no_unguarded_interactive_prompt_call_sites():
    """Every click.prompt/confirm site is a documented, guarded exception."""
    # Arrange
    allowed = set(ALLOWED_PROMPT_SITES)
    # Act
    unexpected = [
        (rel, func, lineno, called)
        for rel, func, lineno, called in _collect_prompt_sites()
        if (rel, func) not in allowed
    ]
    # Assert
    assert not unexpected, (
        "interactive prompt(s) found outside the allowlist:\n"
        + "\n".join(
            f"  {rel}:{lineno}  {called}()  in {func}()"
            for rel, func, lineno, called in unexpected
        )
        + "\n\nA CLI that agents drive must not block on stdin — an "
        "unanswered prompt is a hang, not an error.\n"
        "Fix: accept the value as a CLI option/flag, and for a confirmation "
        "route through scitex_hub._cli._flags.confirm_or_abort (--yes / "
        "--dry-run / non-TTY aware).\n"
        "If the prompt is genuinely intended, guard it with an explicit "
        "sys.stdin.isatty() refusal that names the missing flag, then add it "
        "to ALLOWED_PROMPT_SITES in this file with that reason."
    )


@pytest.mark.parametrize(("site", "reason"), sorted(ALLOWED_PROMPT_SITES.items()))
def test_allowlist_entries_are_still_real(site, reason):
    """A stale allowlist entry is deleted, not left as decoration.

    An entry for a call site that no longer exists silently pre-approves
    the next prompt someone adds to that function.
    """
    # Arrange
    live_sites = {(rel, func) for rel, func, _, _ in _collect_prompt_sites()}
    # Act
    is_live = site in live_sites
    # Assert
    assert is_live, (
        f"ALLOWED_PROMPT_SITES lists {site[0]}::{site[1]}(), but no "
        "click.prompt/confirm call exists there any more. Remove the entry — "
        "a stale exemption pre-approves the next prompt added to that "
        f"function.\nRecorded reason was: {reason}"
    )


# EOF
