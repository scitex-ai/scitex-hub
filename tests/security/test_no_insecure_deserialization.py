"""Mechanical regression barrier for the insecure-deserialization class.

Multi-tenant Django code must NEVER deserialize tenant-influenced bytes with an
executable-object deserializer. Two families are RCE on attacker data:

* pickle / cPickle / marshal / jsonpickle / dill / shelve / ``pandas.read_pickle``
  / ``numpy.load(..., allow_pickle=True)`` — all execute code embedded in the
  stream via ``__reduce__``.
* ``yaml.load`` with the default / Full / Unsafe loader — constructs arbitrary
  Python objects (``!!python/object/apply:os.system`` → RCE). Only
  ``yaml.safe_load`` (SafeLoader) is safe.

The tenant surface that this actually protects: workflow ``yaml_content`` — a
user-editable model field — is deserialized server-side (including in a Celery
worker) at apps/infra/project_app/{views/actions/crud_views.py,
views/workflows/editor.py, models/workflows/workflow.py, tasks/workflow_tasks.py}.
Today every one of those sites uses ``yaml.safe_load``. A silent revert of any of
them to ``yaml.load(...)`` — or the introduction of a ``pickle.loads`` /
``pandas.read_pickle`` on any tenant-reachable path — is a remote-code-execution
regression. ``scitex_io`` maps ``.pkl`` / ``.pickle`` straight to a bare
``pickle.load`` (scitex_io/_load_modules/_pickle.py), so this is not theoretical.

This test FAILS if any such idiom reappears in live code under ``apps/``. It runs
in the security pytest matrix with no database — "a gate that cannot fail is not
a gate". The detector strips COMMENT and STRING tokens before matching, so the
idiom named in a comment or docstring does not trip it — only executable code.
"""
from __future__ import annotations

import io
import re
import tokenize
from pathlib import Path

import pytest

pytestmark = pytest.mark.security

# pickle / marshal / jsonpickle / dill / shelve family + pandas/numpy pickle paths.
_PICKLE = re.compile(r"(?:pickle|cPickle|_pickle)\.loads?\(")
_MARSHAL = re.compile(r"marshal\.loads?\(")
_JSONPICKLE = re.compile(r"jsonpickle\.(?:decode|loads)\(")
_DILL = re.compile(r"dill\.loads?\(")
_SHELVE = re.compile(r"shelve\.open\(")
_READ_PICKLE = re.compile(r"\.read_pickle\(")
_ALLOW_PICKLE = re.compile(r"allow_pickle=True")
# Unsafe YAML loaders (never safe on tenant input).
_YAML_UNSAFE = re.compile(
    r"yaml\.unsafe_load\(|yaml\.full_load\(|FullLoader|UnsafeLoader"
)
# Bare `yaml.load(` — unsafe unless the call explicitly pins a SafeLoader.
_YAML_LOAD = re.compile(r"yaml\.load\(")

_APPS_ROOT = Path(__file__).resolve().parents[2] / "apps"


def _code_lines(source: str) -> dict[int, str]:
    """Reconstruct each physical line from its tokens, dropping COMMENT/STRING.

    Tokens are joined without spaces, which merges adjacent identifiers
    (``return pickle`` -> ``returnpickle``); the idiom regexes therefore avoid a
    leading ``\\b`` and match the dotted call as a substring.

    Returns ``{lineno: code_without_comments_or_strings}``. A comment- or
    docstring-only occurrence of an idiom must NOT trip the gate — only live
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


def find_unsafe_deserialization(source: str) -> list[tuple[int, str]]:
    """Return ``(lineno, reconstructed_code)`` for each insecure-deser hit."""
    hits: list[tuple[int, str]] = []
    for lineno, code in _code_lines(source).items():
        pickle_family = (
            _PICKLE.search(code)
            or _MARSHAL.search(code)
            or _JSONPICKLE.search(code)
            or _DILL.search(code)
            or _SHELVE.search(code)
            or _READ_PICKLE.search(code)
            or _ALLOW_PICKLE.search(code)
        )
        yaml_unsafe = _YAML_UNSAFE.search(code) or (
            _YAML_LOAD.search(code) and "SafeLoader" not in code
        )
        if pickle_family or yaml_unsafe:
            hits.append((lineno, code))
    return hits


def test_no_insecure_deserialization_under_apps():
    """The real gate: no live pickle/unsafe-yaml deserialization under apps/."""
    # Arrange
    py_files = sorted(_APPS_ROOT.rglob("*.py"))
    # Act
    offenders = [
        f"{py.relative_to(_APPS_ROOT.parent)}:{lineno}: {code.strip()}"
        for py in py_files
        for lineno, code in find_unsafe_deserialization(
            py.read_text(encoding="utf-8")
        )
    ]
    # Assert
    assert not offenders, (
        "Insecure deserialization reappeared under apps/. pickle/marshal/"
        "jsonpickle/read_pickle/allow_pickle=True and yaml.load (default/Full/"
        "Unsafe loader) execute code embedded in attacker-controlled bytes. "
        "Tenant workflow yaml_content is deserialized server-side — use "
        "yaml.safe_load; for object formats never unpickle tenant data. "
        "Offenders:\n  " + "\n  ".join(offenders)
    )


def test_detector_flags_bare_yaml_load():
    """Gate-proof (not vacuous): a bare ``yaml.load(`` is detected."""
    # Arrange
    src = "def f(text):\n    return yaml.load(text)\n"
    # Act
    hits = find_unsafe_deserialization(src)
    # Assert
    assert hits, "detector missed a bare yaml.load() call"


def test_detector_flags_pickle_loads():
    """Gate-proof (not vacuous): ``pickle.loads(`` is detected."""
    # Arrange
    src = "def f(blob):\n    return pickle.loads(blob)\n"
    # Act
    hits = find_unsafe_deserialization(src)
    # Assert
    assert hits, "detector missed a pickle.loads() call"


def test_detector_ignores_safe_yaml_and_json():
    """False-positive guard: safe_load / explicit SafeLoader / json.load are fine."""
    # Arrange
    src = (
        "def f(fh, text, jf):\n"
        "    a = yaml.safe_load(fh)\n"
        "    b = yaml.load(text, Loader=yaml.SafeLoader)\n"
        "    c = json.load(jf)\n"
        "    d = yaml.dump(a)\n"
        "    return (a, b, c, d)\n"
    )
    # Act
    hits = find_unsafe_deserialization(src)
    # Assert
    assert hits == [], "detector false-positived on safe deserialization"


def test_detector_ignores_the_idiom_in_comments_and_docstrings():
    """The idiom named in a comment/docstring must not trip the gate."""
    # Arrange
    src = (
        "def f(text):\n"
        "    # do NOT use yaml.load(text) or pickle.loads(text) here\n"
        '    """Historically this called yaml.load(text)."""\n'
        "    return yaml.safe_load(text)\n"
    )
    # Act
    hits = find_unsafe_deserialization(src)
    # Assert
    assert hits == [], "detector tripped on a comment/docstring mention"
