"""Mechanical regression barrier for the prefix-match path-containment class.

`str(target.resolve()).startswith(str(root.resolve()))` is NOT path containment:
a root of ``/data/proj`` admits ``/data/proj-other`` (a prefix *sibling*), and one
such site was cross-tenant — bob could read bob123's files (PR #441). The whole
class (~30 sites) was converted to ``validate_path_in_project`` /
``validate_path_in_user_jail`` (``target.resolve().relative_to(root.resolve())``)
at ``apps/infra/project_app/services/filesystem/permissions.py`` — see card
sec-prefix-path-containment-class.

This test FAILS if the vulnerable idiom reappears anywhere under ``apps/``, so a
regression is loud and blocking (it runs in the required pytest matrix), not a
written warning that a future edit can silently ignore — "a gate that cannot fail
is not a gate". CodeQL's barrier model (PR #461) is the second layer; this is the
first-party, required-check layer.

The detector strips COMMENT and STRING tokens before matching, so the idiom
*documented* in a comment or docstring (e.g. execution.py) does not trip the gate
— only live code does.
"""
from __future__ import annotations

import io
import re
import tokenize
from pathlib import Path

import pytest

pytestmark = pytest.mark.security

# `.resolve()).startswith(`  or  `.resolve().startswith(`  — a call chained off resolve().
_CHAINED = re.compile(r"\.resolve\(\)\)?\.startswith\(")
# `.startswith(str(<expr>.resolve()`  — resolve() inside the startswith argument.
_ARG = re.compile(r"\.startswith\(\s*str\([^)]*\.resolve\(\)")

_APPS_ROOT = Path(__file__).resolve().parents[2] / "apps"


def _code_lines(source: str) -> dict[int, str]:
    """Reconstruct each physical line from its tokens, dropping COMMENT/STRING.

    Returns ``{lineno: code_without_comments_or_strings}``. A comment- or
    docstring-only occurrence of the idiom must NOT trip the gate — only live
    code. On an unparseable file we fall back to the raw lines rather than
    silently skipping it (fail loud, never mask).
    """
    per_line: dict[int, list[str]] = {}
    try:
        for tok in tokenize.generate_tokens(io.StringIO(source).readline):
            if tok.type in (tokenize.COMMENT, tokenize.STRING):
                continue
            (srow, _), (erow, _) = tok.start, tok.end
            if srow == erow and tok.string:
                per_line.setdefault(srow, []).append(tok.string)
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return {i: ln for i, ln in enumerate(source.splitlines(), start=1)}
    return {ln: "".join(toks) for ln, toks in per_line.items()}


def find_prefix_containment(source: str) -> list[tuple[int, str]]:
    """Return ``(lineno, reconstructed_code)`` for each prefix-match containment hit."""
    hits: list[tuple[int, str]] = []
    for lineno, code in _code_lines(source).items():
        if _CHAINED.search(code) or _ARG.search(code):
            hits.append((lineno, code))
    return hits


def test_no_prefix_match_path_containment_under_apps():
    """The real gate: no live ``resolve()+startswith`` containment check under apps/."""
    # Arrange
    py_files = sorted(_APPS_ROOT.rglob("*.py"))
    # Act
    offenders = [
        f"{py.relative_to(_APPS_ROOT.parent)}:{lineno}: {code.strip()}"
        for py in py_files
        for lineno, code in find_prefix_containment(py.read_text(encoding="utf-8"))
    ]
    # Assert
    assert not offenders, (
        "Prefix-match path containment reappeared. `str.startswith` is NOT containment: "
        "a root of /data/proj admits /data/proj-other, and one such site was cross-tenant "
        "(PR #441). Use validate_path_in_project() / validate_path_in_user_jail() from "
        "apps/infra/project_app/services/filesystem/permissions.py "
        "(target.resolve().relative_to(root.resolve())). Offenders:\n  "
        + "\n  ".join(offenders)
    )


def test_detector_flags_chained_resolve_startswith():
    """Gate-proof (not vacuous): the ``.resolve()).startswith(`` idiom is detected."""
    # Arrange
    src = "def f(t, r):\n    return str(t.resolve()).startswith(str(r.resolve()))\n"
    # Act
    hits = find_prefix_containment(src)
    # Assert
    assert hits, "detector missed the chained resolve()+startswith idiom"


def test_detector_flags_resolve_in_startswith_argument():
    """Gate-proof (not vacuous): ``resolve()`` inside the startswith argument is detected."""
    # Arrange
    src = (
        "def f(t, r):\n"
        "    resolved = t.resolve()\n"
        "    return str(resolved).startswith(str(r.resolve()))\n"
    )
    # Act
    hits = find_prefix_containment(src)
    # Assert
    assert hits, "detector missed the resolve()-in-argument idiom"


def test_detector_ignores_legitimate_startswith():
    """False-positive guard: ordinary startswith (hidden-file / URL / scheme) is fine."""
    # Arrange
    src = (
        "def f(name, path, url):\n"
        "    if name.startswith('.'):\n"
        "        return True\n"
        "    if path.startswith('/apps/'):\n"
        "        return True\n"
        "    return url.startswith('git@')\n"
    )
    # Act
    hits = find_prefix_containment(src)
    # Assert
    assert hits == [], "detector false-positived on legitimate startswith"


def test_detector_ignores_the_idiom_in_comments_and_docstrings():
    """The idiom documented in a comment/docstring (e.g. execution.py:87) must not trip."""
    # Arrange
    src = (
        "def f(t, r):\n"
        "    # str(t.resolve()).startswith(str(r.resolve()))  <- old buggy form\n"
        '    """Replaces str(t.resolve()).startswith(str(r.resolve()))."""\n'
        "    return t == r\n"
    )
    # Act
    hits = find_prefix_containment(src)
    # Assert
    assert hits == [], "detector tripped on a comment/docstring mention"
