#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A secret-shaped setting must not fall back to a usable literal.

WHY THIS EXISTS — a real incident, 2026-08-16.

``apps/workspace/dev_app/management/commands/init_test_user.py`` read::

    DEFAULT_PASSWORD = os.getenv("SCITEX_HUB_TEST_USER_PASSWORD", "Password123!")

That literal was not a placeholder. It was a SHARED credential: every deployment
that omitted the env var converged on the same value, this repository is PUBLIC,
and the password was additionally printed in the README, the setup page and the
docs. On 2026-08-16 it was found to authenticate as ``test-user`` on
PRODUCTION. The account was closed and the env value rotated the same day; this
guard closes the code path that recreates it.

WHAT IS AND IS NOT FORBIDDEN.

The rule is NOT "no string literals near the word password" — that would flag
correct code such as::

    SCITEX_HUB_DB_PASSWORD_DEV: scitex_test_pass  # pragma: allowlist secret

which is fine: scoped to an ephemeral CI database, and explicitly DECLARED as a
deliberate exception. A blanket ban would flag that line too, and a guard that
cries wolf gets switched off — which is worse than no guard.

The rule is: a secret-shaped env lookup may not supply a **usable** default.
Either the fallback is empty (the honest "not configured"), or the line carries
an explicit ``# pragma: allowlist secret`` stating that somebody decided.

Detection is AST-based, not textual: a regex over source would match this very
docstring, and would miss ``os.environ.get`` spelled across two lines.
"""

import ast
from pathlib import Path

import pytest

# Anything whose NAME says "this is a credential".
SECRET_NAME_MARKERS = ("PASSWORD", "SECRET", "TOKEN", "PASSWD", "APIKEY", "API_KEY")

# The specific credential from the 2026-08-16 incident. Split so this file is
# not itself a textual hit for anyone grepping the repo for it.
BURNED_CREDENTIAL = "Password" + "123!"

ALLOW_PRAGMA = "pragma: allowlist secret"

SKIP_DIRS = {
    ".git",
    ".worktrees",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    ".tox",
    "build",
    "dist",
    ".mypy_cache",
    ".pytest_cache",
    "_docs",
}

BAD_SAMPLE = (
    "import os\n"
    'DEFAULT_PASSWORD = os.getenv("SCITEX_HUB_TEST_USER_PASSWORD", "'
    + BURNED_CREDENTIAL
    + '")\n'
)

GOOD_SAMPLES = [
    # empty default — the fix shipped alongside this guard
    'import os\nP = os.getenv("SCITEX_HUB_TEST_USER_PASSWORD", "")\n',
    # no default at all
    'import os\nP = os.getenv("SCITEX_HUB_TEST_USER_PASSWORD")\n',
    # explicitly declared exception
    'import os\nP = os.getenv("CI_PASSWORD", "eph")  # pragma: allowlist secret\n',
    # declared exception on a WRAPPED call — the pragma lands on the closing
    # paren, not the first line. Formatters produce this shape routinely, and
    # a first-line-only pragma check silently ignores it (it did, here, until
    # config/settings/settings_dev.py got wrapped and started failing).
    (
        "import os\n"
        "P = os.environ.get(\n"
        '    "CI_PASSWORD", "eph"\n'
        ")  # pragma: allowlist secret\n"
    ),
    # not a secret-shaped name
    'import os\nH = os.getenv("SCITEX_HUB_DB_HOST_DEV", "localhost")\n',
]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _python_files(root: Path):
    # Match SKIP_DIRS against the path RELATIVE to the repo root, never the
    # absolute path. When this runs inside a linked worktree the root is itself
    # ".../.worktrees/<name>/", so an absolute-path check matches ".worktrees"
    # on EVERY file and the scan silently visits nothing — passing by measuring
    # zero. That is the exact "a gate that cannot fail is not a gate" defect
    # this file exists to catch, and it shipped here first time round.
    for path in root.rglob("*.py"):
        if any(part in SKIP_DIRS for part in path.relative_to(root).parts):
            continue
        yield path


def _is_secret_name(name: str) -> bool:
    upper = name.upper()
    return any(marker in upper for marker in SECRET_NAME_MARKERS)


def _env_lookup_default(node: ast.AST):
    """Return ``(env_name, default_literal)`` for a 2-arg env lookup, else None.

    Matches ``os.getenv(NAME, DEFAULT)`` and ``os.environ.get(NAME, DEFAULT)``.
    """
    if not isinstance(node, ast.Call) or len(node.args) != 2:
        return None
    func = node.func
    if not isinstance(func, ast.Attribute):
        return None
    if func.attr not in ("getenv", "get"):
        return None
    name_arg, default_arg = node.args
    if not isinstance(name_arg, ast.Constant) or not isinstance(name_arg.value, str):
        return None
    if not isinstance(default_arg, ast.Constant) or not isinstance(
        default_arg.value, str
    ):
        return None
    return name_arg.value, default_arg.value


def find_usable_secret_defaults(source: str, filename: str = "<memory>"):
    """Yield ``(lineno, env_name, default)`` for every violation in ``source``."""
    try:
        tree = ast.parse(source, filename=filename)
    except SyntaxError:
        return
    lines = source.splitlines()
    for node in ast.walk(tree):
        found = _env_lookup_default(node)
        if found is None:
            continue
        env_name, default = found
        if not default:  # empty default is the honest "not configured"
            continue
        if not _is_secret_name(env_name):
            continue
        # Look for the pragma across the call's WHOLE line span, not just its
        # first line. A formatter that wraps the call puts the trailing comment
        # on the closing-paren line, and a first-line-only check then ignores a
        # pragma that is plainly there — making the declared-exception escape
        # hatch silently unusable for exactly the long lines most likely to
        # need it.
        start = node.lineno
        end = getattr(node, "end_lineno", None) or node.lineno
        span = lines[start - 1 : end]
        if any(ALLOW_PRAGMA in line for line in span):
            continue
        yield node.lineno, env_name, default


def _scan_repo():
    """Return violation strings for every Python file in the repository."""
    root = _repo_root()
    violations = []
    for path in _python_files(root):
        try:
            source = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for lineno, env_name, default in find_usable_secret_defaults(source, str(path)):
            violations.append(
                f"{path.relative_to(root)}:{lineno} {env_name} falls back to a "
                f"usable literal ({len(default)} chars)"
            )
    return violations


def _scan_repo_for_burned_credential():
    """Return ``path:lineno`` for every default equal to the burned password."""
    root = _repo_root()
    here = Path(__file__).resolve()
    offenders = []
    for path in _python_files(root):
        if path.resolve() == here:
            continue
        try:
            source = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for lineno, _env_name, default in find_usable_secret_defaults(
            source, str(path)
        ):
            if default == BURNED_CREDENTIAL:
                offenders.append(f"{path.relative_to(root)}:{lineno}")
    return offenders


# ---------------------------------------------------------------------------
# The detector must be able to go RED. A guard never observed failing is not a
# guard, and the repo-wide assertions below are worthless without these.
# ---------------------------------------------------------------------------


def test_detector_finds_exactly_one_violation_in_the_pre_fix_line():
    # Arrange: the literal line as it stood before 2026-08-16.
    source = BAD_SAMPLE
    # Act
    hits = list(find_usable_secret_defaults(source))
    # Assert
    assert len(hits) == 1


def test_detector_reports_the_offending_env_var_name():
    # Arrange
    source = BAD_SAMPLE
    # Act
    _lineno, env_name, _default = next(iter(find_usable_secret_defaults(source)))
    # Assert
    assert env_name == "SCITEX_HUB_TEST_USER_PASSWORD"


def test_detector_reports_the_burned_default_value():
    # Arrange
    source = BAD_SAMPLE
    # Act
    _lineno, _env_name, default = next(iter(find_usable_secret_defaults(source)))
    # Assert
    assert default == BURNED_CREDENTIAL


@pytest.mark.parametrize("source", GOOD_SAMPLES)
def test_detector_does_not_flag_correct_code(source):
    # Arrange: each sample is correct code that must stay unflagged.
    expected = []
    # Act
    hits = list(find_usable_secret_defaults(source))
    # Assert
    assert hits == expected


# ---------------------------------------------------------------------------
# The actual assertions against this repository.
# ---------------------------------------------------------------------------

# The two repo-wide assertions below are only meaningful if the scan actually
# reads files. A path bug that yields nothing makes them pass while testing
# nothing — which is precisely what happened on the first draft of this file.
# This floor is the control. It is deliberately far below the true count so it
# fails on "the scan is broken", never on "somebody deleted a module".
MIN_PYTHON_FILES_SCANNED = 200


def test_the_repo_scan_actually_visits_python_files():
    # Arrange
    root = _repo_root()
    # Act
    scanned = sum(1 for _ in _python_files(root))
    # Assert
    assert scanned > MIN_PYTHON_FILES_SCANNED, (
        f"only {scanned} Python files scanned under {root} — the repo-wide "
        "secret-default assertions are passing vacuously. Check SKIP_DIRS "
        "against paths RELATIVE to the root."
    )


def test_no_secret_setting_falls_back_to_a_usable_literal():
    # Arrange
    remedy = (
        "A secret-shaped setting falls back to a usable literal. Every "
        "deployment that omits the env var converges on this same value, and "
        "this repository is public.\nFix: use an empty default, or add "
        "'# pragma: allowlist secret' with a reason if the value is genuinely "
        "non-usable (e.g. an ephemeral CI database).\n\n"
    )
    # Act
    violations = _scan_repo()
    # Assert
    assert not violations, remedy + "\n".join(violations)


def test_the_burned_credential_is_not_a_default_anywhere_in_python():
    # Arrange
    remedy = (
        f"{BURNED_CREDENTIAL!r} authenticated as test-user on PRODUCTION on "
        "2026-08-16. It must never be a code default again.\n"
    )
    # Act
    offenders = _scan_repo_for_burned_credential()
    # Assert
    assert not offenders, remedy + "\n".join(offenders)
